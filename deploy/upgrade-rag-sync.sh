#!/bin/bash
# upgrade-rag-sync.sh — Ingestion WordPress directe + endpoint auto-sync n8n
# 1) Module rag/wp_ingest.py  2) Runner /root/reingest_wp.py
# 3) Endpoint /api/ingest-article  4) Secret dans .env  5) Restart
set -e
DIR=/opt/RAG-Gemini
APP=$DIR/app.py

echo "1/6 — Dépendances (venv)..."
$DIR/venv/bin/pip install -q beautifulsoup4 requests
echo "   ✅"

echo "2/6 — Module rag/wp_ingest.py..."
cat > $DIR/rag/wp_ingest.py << 'WPEOF'
"""Ingestion d'articles WordPress (lhusser.fr) via l'API REST.
IDs déterministes wp-{post_id}-{chunk} : réingérer un article écrase ses vecteurs."""
import re, time, logging, requests
from bs4 import BeautifulSoup
from rag.embedder import embed_text
from rag.indexer import get_index, upsert_batch
from rag.ingest import chunk_text

WP_BASE = "https://lhusser.fr/wp-json/wp/v2"
_FIELDS = "id,title,link,content,categories,date"
_cats = None


def get_categories():
    global _cats
    if _cats is None:
        _cats = {}
        try:
            r = requests.get(f"{WP_BASE}/categories", params={"per_page": 100}, timeout=30)
            for c in (r.json() if r.status_code == 200 else []):
                _cats[c["id"]] = c["name"]
        except Exception as e:
            logging.warning("get_categories: %s", e)
    return _cats


def extract_text(html):
    """Texte intégral de l'article (toutes les sections custom incluses)."""
    soup = BeautifulSoup(html or "", "html.parser")
    for t in soup(["script", "style", "noscript", "iframe", "svg"]):
        t.decompose()
    txt = soup.get_text(separator="\n")
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    txt = re.sub(r"[ \t]{2,}", " ", txt)
    return txt.strip()


def fetch_posts():
    """Tous les articles publiés, paginés par 100."""
    page = 1
    while True:
        r = requests.get(f"{WP_BASE}/posts",
                         params={"per_page": 100, "page": page, "_fields": _FIELDS},
                         timeout=60)
        if r.status_code != 200:
            break
        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break
        for p in batch:
            yield p
        if len(batch) < 100:
            break
        page += 1


def fetch_post(post_id=None, url=None):
    """Un article par ID ou par URL (slug)."""
    try:
        if post_id:
            r = requests.get(f"{WP_BASE}/posts/{int(post_id)}",
                             params={"_fields": _FIELDS}, timeout=30)
            return r.json() if r.status_code == 200 else None
        if url:
            slug = url.rstrip("/").split("/")[-1].split("?")[0]
            r = requests.get(f"{WP_BASE}/posts",
                             params={"slug": slug, "_fields": _FIELDS}, timeout=30)
            arr = r.json() if r.status_code == 200 else []
            return arr[0] if arr else None
    except Exception as e:
        logging.warning("fetch_post: %s", e)
    return None


def delete_article_vectors(post_id):
    """Supprime les vecteurs existants d'un article (par préfixe d'ID)."""
    try:
        idx = get_index()
        ids = []
        for page in idx.list(prefix=f"wp-{post_id}-"):
            ids.extend(page)
        if ids:
            idx.delete(ids=ids)
    except Exception as e:
        logging.warning("delete_article_vectors %s: %s", post_id, e)


def ingest_post(p, pause=0.3):
    """Indexe un article : extraction, chunking, embeddings, upsert. Retourne le nb de chunks."""
    pid = p["id"]
    title = BeautifulSoup(p.get("title", {}).get("rendered", ""), "html.parser").get_text().strip()
    url = p.get("link", "")
    cats = get_categories()
    cat = ", ".join(cats.get(c, "") for c in p.get("categories", []) if cats.get(c)) or "Blog"
    body = extract_text(p.get("content", {}).get("rendered", ""))
    if not body:
        return 0
    header = f"Article : {title}\nCatégorie : {cat}\nAuteur : Laurent Husser\nURL : {url}\n\n"
    delete_article_vectors(pid)
    vectors = []
    for i, c in enumerate(chunk_text(body)):
        emb = embed_text(header + c)
        time.sleep(pause)  # respect du rate limit Gemini
        if not emb:
            continue
        vectors.append({
            "id": f"wp-{pid}-{i}",
            "values": emb,
            "metadata": {
                "source": "lhusser.fr", "source_type": "wordpress_post",
                "article": title, "title": title, "url": url,
                "category": cat, "date": (p.get("date", "") or "")[:10],
                "chunk": i, "text": header + c,
            },
        })
    if body and not vectors:
        raise RuntimeError("aucun embedding généré (quota Gemini ?) — article à retenter")
    if vectors:
        upsert_batch(vectors)
    return len(vectors)


def purge_legacy():
    """Supprime les vecteurs de l'ancien export XML (IDs ne commençant pas par wp-)."""
    try:
        idx = get_index()
        legacy = []
        for page in idx.list():
            legacy.extend([i for i in page if not str(i).startswith("wp-")])
        for j in range(0, len(legacy), 500):
            idx.delete(ids=legacy[j:j + 500])
        return len(legacy)
    except Exception as e:
        logging.warning("purge_legacy: %s", e)
        return -1
WPEOF
$DIR/venv/bin/python3 -c "import sys; sys.path.insert(0,'$DIR'); import ast; ast.parse(open('$DIR/rag/wp_ingest.py').read())"
echo "   ✅"

echo "3/6 — Runner /root/reingest_wp.py..."
cat > /root/reingest_wp.py << 'RUNEOF'
#!/usr/bin/env python3
"""Réingestion complète lhusser.fr → Pinecone, avec reprise sur incident."""
import os, sys, time
sys.path.insert(0, "/opt/RAG-Gemini")
os.chdir("/opt/RAG-Gemini")
from dotenv import load_dotenv
load_dotenv("/opt/RAG-Gemini/.env")
from rag.wp_ingest import fetch_posts, ingest_post, purge_legacy

DONE = "/root/.reingest_done.txt"
done = set()
if os.path.exists(DONE):
    done = set(x.strip() for x in open(DONE) if x.strip())

posts = list(fetch_posts())
print(f"📚 {len(posts)} articles publiés — {len(done)} déjà indexés (reprise)", flush=True)

errors, total = 0, 0
for n, p in enumerate(posts, 1):
    pid = str(p["id"])
    title = p.get("title", {}).get("rendered", "?")[:55]
    if pid in done:
        continue
    try:
        c = ingest_post(p)
        total += c
        with open(DONE, "a") as f:
            f.write(pid + "\n")
        print(f"({n}/{len(posts)}) ✅ {c:>3} chunks — {title}", flush=True)
    except Exception as e:
        errors += 1
        print(f"({n}/{len(posts)}) ❌ {title} : {e}", flush=True)
        time.sleep(5)

print(f"\n🎉 {total} nouveaux chunks indexés, {errors} erreur(s).", flush=True)
if errors:
    print("⚠️  Relance le script pour reprendre les articles en erreur (la purge attendra).", flush=True)
else:
    print("🧹 Purge des anciens vecteurs (export XML)...", flush=True)
    n = purge_legacy()
    print(f"   {n} anciens vecteurs supprimés. Index 100% à jour ! 🚀" if n >= 0
          else "   ⚠️ Purge impossible automatiquement — dis-le à Claude.", flush=True)
RUNEOF
echo "   ✅"

echo "4/6 — Secret d'ingestion dans .env..."
if ! grep -q "RAG_INGEST_SECRET" $DIR/.env 2>/dev/null; then
    SECRET=$(openssl rand -hex 24)
    echo "RAG_INGEST_SECRET=$SECRET" >> $DIR/.env
else
    SECRET=$(grep "RAG_INGEST_SECRET" $DIR/.env | cut -d= -f2)
fi
echo "   ✅"

echo "5/6 — Endpoint /api/ingest-article dans app.py..."
cp "$APP" "$APP.bak-sync-$(date +%Y%m%d-%H%M%S)"
$DIR/venv/bin/python3 << 'PATCHEOF'
import io
APP = "/opt/RAG-Gemini/app.py"
with io.open(APP, encoding="utf-8") as f:
    s = f.read()

if "/api/ingest-article" in s:
    print("   (déjà présent, rien à faire)")
else:
    anchor = '@app.route("/")\ndef index():'
    assert s.count(anchor) == 1, "Anchor index() introuvable/multiple"
    endpoint = '''@app.route("/api/ingest-article", methods=["POST"])
def api_ingest_article():
    """Indexe ou réindexe UN article lhusser.fr — appelé par n8n à chaque publication.
    Auth : header X-Ingest-Secret ou champ JSON "secret" (= RAG_INGEST_SECRET du .env)."""
    from dotenv import load_dotenv; load_dotenv()
    want = _os.environ.get("RAG_INGEST_SECRET", "")
    d = request.get_json(silent=True) or {}
    got = request.headers.get("X-Ingest-Secret") or d.get("secret", "")
    if not want or got != want:
        return jsonify({"error": "Secret invalide"}), 401
    from rag.wp_ingest import fetch_post, ingest_post
    p = fetch_post(post_id=d.get("id"), url=d.get("url") or "")
    if not p:
        return jsonify({"error": "Article introuvable", "id": d.get("id"), "url": d.get("url")}), 404
    n = ingest_post(p)
    return jsonify({"ok": True, "id": p["id"], "chunks": n})

'''
    s = s.replace(anchor, endpoint + anchor)
    with io.open(APP, "w", encoding="utf-8") as f:
        f.write(s)
    print("   ✅ Endpoint ajouté")
PATCHEOF
$DIR/venv/bin/python3 -m py_compile "$APP" && echo "   ✅ Syntaxe OK"

echo "6/6 — Redémarrage + test..."
systemctl restart rag-gemini
sleep 3
systemctl is-active rag-gemini
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:5000/api/ingest-article \
  -H 'Content-Type: application/json' -d '{"secret":"mauvais"}')
echo "   Test mauvais secret → HTTP $code (attendu : 401)"

echo ""
echo "═══════════════════════════════════════════════════"
echo "✅ Installation terminée !"
echo ""
echo "🔑 SECRET pour n8n (à coller dans le workflow) :"
echo "   $SECRET"
echo ""
echo "▶️  Lancer la réingestion complète (1-2 h, en arrière-plan) :"
echo "   nohup /opt/RAG-Gemini/venv/bin/python3 /root/reingest_wp.py > /root/reingest_wp.log 2>&1 &"
echo ""
echo "👀 Suivre la progression :"
echo "   tail -f /root/reingest_wp.log"
echo "═══════════════════════════════════════════════════"
