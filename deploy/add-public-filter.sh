#!/bin/bash
# add-public-filter.sh — Les endpoints publics ne voient QUE les articles du blog
# (les fichiers uploadés via rag.lhusser.cloud resteront invisibles du chat public)
set -e
APP=/opt/RAG-Gemini/app.py

echo "1/3 — Sauvegarde + patch..."
cp "$APP" "$APP.bak-filter-$(date +%Y%m%d-%H%M%S)"
/opt/RAG-Gemini/venv/bin/python3 << 'PYEOF'
import io
APP = "/opt/RAG-Gemini/app.py"
with io.open(APP, encoding="utf-8") as f:
    s = f.read()

old = "result = answer_question(q, top_k=top_k)"
new = 'result = answer_question(q, top_k=top_k, source_filter="lhusser.fr")'
n = s.count(old)
assert n == 2, f"Attendu 2 occurrences (/query et /api/public-query), trouvé {n}"
s = s.replace(old, new)

with io.open(APP, "w", encoding="utf-8") as f:
    f.write(s)
print("   ✅ Filtre appliqué aux 2 endpoints publics")
PYEOF

echo "2/3 — Vérification + redémarrage..."
/opt/RAG-Gemini/venv/bin/python3 -m py_compile "$APP" && echo "   ✅ Syntaxe OK"
systemctl restart rag-gemini
sleep 3
systemctl is-active rag-gemini

echo "3/3 — Test réel (1 question, ~1 centime)..."
curl -s -X POST http://127.0.0.1:5000/api/public-query \
  -H 'Content-Type: application/json' \
  -d '{"question":"Parle-moi de Claude Fable 5"}' | head -c 700
echo ""
echo ""
echo "✅ Terminé ! Vérifie que la réponse ci-dessus cite des articles avec leurs URLs."
