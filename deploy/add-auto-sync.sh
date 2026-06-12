#!/bin/bash
# add-auto-sync.sh — Auto-indexation des nouveaux articles toutes les 15 min (cron)
# Vérifie les 10 derniers articles WP et n'ingère QUE ceux absents de Pinecone.
set -e
DIR=/opt/RAG-Gemini
APP=$DIR/app.py
WPI=$DIR/rag/wp_ingest.py

echo "1/5 — Fonctions de synchronisation dans rag/wp_ingest.py..."
cp "$WPI" "$WPI.bak-$(date +%Y%m%d-%H%M%S)"
$DIR/venv/bin/python3 << 'PYEOF'
import io
WPI = "/opt/RAG-Gemini/rag/wp_ingest.py"
with io.open(WPI, encoding="utf-8") as f:
    s = f.read()

if "def sync_latest" in s:
    print("   (déjà présent)")
else:
    s += '''

def article_indexed(post_id):
    """Vrai si le premier chunk de l'article existe déjà dans Pinecone."""
    try:
        idx = get_index()
        res = idx.fetch(ids=["wp-%s-0" % post_id])
        vecs = getattr(res, "vectors", None)
        if vecs is None and isinstance(res, dict):
            vecs = res.get("vectors")
        return bool(vecs)
    except Exception as e:
        logging.warning("article_indexed %s: %s", post_id, e)
        return False


def sync_latest(n=10):
    """Indexe les articles récents absents de l'index. Idempotent et économe :
    si tout est déjà indexé, aucun appel d'embedding n'est effectué."""
    done = []
    try:
        r = requests.get(f"{WP_BASE}/posts",
                         params={"per_page": min(int(n), 25), "_fields": _FIELDS},
                         timeout=30)
        for p in (r.json() if r.status_code == 200 else []):
            if article_indexed(p["id"]):
                continue
            c = ingest_post(p)
            title = BeautifulSoup(p.get("title", {}).get("rendered", ""), "html.parser").get_text()
            done.append({"id": p["id"], "title": title[:80], "chunks": c})
    except Exception as e:
        logging.warning("sync_latest: %s", e)
    return done
'''
    with io.open(WPI, "w", encoding="utf-8") as f:
        f.write(s)
    print("   ✅ article_indexed() + sync_latest() ajoutés")
PYEOF
$DIR/venv/bin/python3 -m py_compile "$WPI" && echo "   ✅ Syntaxe OK"

echo "2/5 — Endpoint /api/sync-latest dans app.py..."
cp "$APP" "$APP.bak-sync2-$(date +%Y%m%d-%H%M%S)"
$DIR/venv/bin/python3 << 'PYEOF'
import io
APP = "/opt/RAG-Gemini/app.py"
with io.open(APP, encoding="utf-8") as f:
    s = f.read()

if "/api/sync-latest" in s:
    print("   (déjà présent)")
else:
    anchor = '@app.route("/")\ndef index():'
    assert s.count(anchor) == 1
    endpoint = '''@app.route("/api/sync-latest", methods=["POST"])
def api_sync_latest():
    """Indexe les derniers articles manquants — appelé par le cron toutes les 15 min."""
    from dotenv import load_dotenv; load_dotenv()
    want = _os.environ.get("RAG_INGEST_SECRET", "")
    d = request.get_json(silent=True) or {}
    got = request.headers.get("X-Ingest-Secret") or d.get("secret", "")
    if not want or got != want:
        return jsonify({"error": "Secret invalide"}), 401
    from rag.wp_ingest import sync_latest
    res = sync_latest(int(d.get("n", 10) or 10))
    return jsonify({"ok": True, "count": len(res), "ingested": res})

'''
    s = s.replace(anchor, endpoint + anchor)
    with io.open(APP, "w", encoding="utf-8") as f:
        f.write(s)
    print("   ✅ Endpoint ajouté")
PYEOF
$DIR/venv/bin/python3 -m py_compile "$APP" && echo "   ✅ Syntaxe OK"

echo "3/5 — Redémarrage..."
systemctl restart rag-gemini
sleep 3
systemctl is-active rag-gemini

echo "4/5 — Cron toutes les 15 minutes..."
SECRET=$(grep "^RAG_INGEST_SECRET" $DIR/.env | cut -d= -f2)
CRON_CMD="*/15 * * * * curl -s -X POST http://127.0.0.1:5000/api/sync-latest -H 'Content-Type: application/json' -d '{\"secret\":\"$SECRET\"}' >> /root/rag-sync.log 2>&1"
( crontab -l 2>/dev/null | grep -v "api/sync-latest" ; echo "$CRON_CMD" ) | crontab -
crontab -l | grep -q "sync-latest" && echo "   ✅ Cron installé"

echo "5/5 — Test immédiat (ingère ton article du jour s'il manque)..."
curl -s -X POST http://127.0.0.1:5000/api/sync-latest \
  -H 'Content-Type: application/json' \
  -d "{\"secret\":\"$SECRET\"}"
echo ""
echo ""
echo "✅ Auto-sync opérationnel ! Chaque article publié sera indexé dans les 15 min."
echo "   Journal : tail -5 /root/rag-sync.log"
