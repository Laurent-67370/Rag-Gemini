#!/bin/bash
# add-public-articles.sh — Crée l'endpoint /api/public-articles attendu par le widget
# → compteur exact d'articles, suggestions réelles, onglet Recherche fonctionnel
set -e
APP=/opt/RAG-Gemini/app.py

echo "1/3 — Sauvegarde + ajout de l'endpoint..."
cp "$APP" "$APP.bak-articles-$(date +%Y%m%d-%H%M%S)"
/opt/RAG-Gemini/venv/bin/python3 << 'PYEOF'
import io
APP = "/opt/RAG-Gemini/app.py"
with io.open(APP, encoding="utf-8") as f:
    s = f.read()

if "/api/public-articles" in s:
    print("   (déjà présent, rien à faire)")
else:
    anchor = '@app.route("/")\ndef index():'
    assert s.count(anchor) == 1, "Anchor index() introuvable/multiple"
    endpoint = '''_articles_cache = {"t": 0, "data": []}

@app.route("/api/public-articles")
def api_public_articles():
    """Liste publique des articles du blog (titre, url, catégorie, date) — cache 1 h."""
    import time, html as _h
    if time.time() - _articles_cache["t"] > 3600 or not _articles_cache["data"]:
        try:
            import requests as _rq
            cats = {}
            r = _rq.get("https://lhusser.fr/wp-json/wp/v2/categories",
                        params={"per_page": 100}, timeout=20)
            for c in (r.json() if r.ok else []):
                cats[c["id"]] = c["name"]
            arts, page = [], 1
            while True:
                r = _rq.get("https://lhusser.fr/wp-json/wp/v2/posts",
                            params={"per_page": 100, "page": page,
                                    "_fields": "id,title,link,categories,date"},
                            timeout=30)
                if r.status_code != 200:
                    break
                batch = r.json()
                if not isinstance(batch, list) or not batch:
                    break
                for p in batch:
                    arts.append({
                        "id": p["id"],
                        "title": _h.unescape(p.get("title", {}).get("rendered", "")),
                        "url": p.get("link", ""),
                        "category": ", ".join(cats.get(c, "") for c in p.get("categories", []) if cats.get(c)),
                        "date": (p.get("date", "") or "")[:10],
                    })
                if len(batch) < 100:
                    break
                page += 1
            if arts:
                _articles_cache["data"] = arts
                _articles_cache["t"] = time.time()
        except Exception:
            pass
    return jsonify({"articles": _articles_cache["data"],
                    "total": len(_articles_cache["data"])})

'''
    s = s.replace(anchor, endpoint + anchor)
    with io.open(APP, "w", encoding="utf-8") as f:
        f.write(s)
    print("   ✅ Endpoint /api/public-articles ajouté (cache 1 h)")
PYEOF
/opt/RAG-Gemini/venv/bin/python3 -m py_compile "$APP" && echo "   ✅ Syntaxe OK"

echo "2/3 — Redémarrage..."
systemctl restart rag-gemini
sleep 3
systemctl is-active rag-gemini

echo "3/3 — Test (le 1er appel construit le cache, ~5 s)..."
curl -s "http://127.0.0.1:5000/api/public-articles" | head -c 250
echo ""
TOTAL=$(curl -s "http://127.0.0.1:5000/api/public-articles" | grep -o '"total": *[0-9]*' | grep -o '[0-9]*')
echo ""
echo "✅ Terminé ! Total d'articles renvoyé : $TOTAL (attendu : 429)"
echo "   Purge LiteSpeed + navigation privée → l'entête affichera le nombre exact."
