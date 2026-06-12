#!/bin/bash
# fix-sources-display.sh — Supprime la section "Sources :" en texte brut des réponses
# 1) Le LLM ne génère plus de liste de sources (les cartes cliquables s'en chargent)
# 2) La copie VPS du widget est synchronisée avec la v2.0.1 du plugin WordPress
set -e
RET=/opt/RAG-Gemini/rag/retriever.py

echo "1/3 — Prompt système du retriever..."
cp "$RET" "$RET.bak-$(date +%Y%m%d-%H%M%S)"
/opt/RAG-Gemini/venv/bin/python3 << 'PYEOF'
import io
RET = "/opt/RAG-Gemini/rag/retriever.py"
with io.open(RET, encoding="utf-8") as f:
    s = f.read()

old = ('    sys = ("Tu es l\'assistant du blog lhusser.fr. Réponds uniquement depuis le contexte fourni, en français. "\n'
       '           "Quand la source est un article du blog (étiquette [ARTICLE]), cite-le dans la section Sources "\n'
       '           "sous la forme : titre de l\'article suivi de son lien URL. Ne mentionne jamais les noms de fichiers XML.")')
new = ('    sys = ("Tu es l\'assistant du blog lhusser.fr. Réponds uniquement depuis le contexte fourni, en français. "\n'
       '           "N\'ajoute JAMAIS de section Sources ni de liste de liens en fin de réponse : "\n'
       '           "l\'interface affiche déjà les sources sous forme de cartes cliquables. "\n'
       '           "Tu peux citer le titre d\'un article dans le fil du texte si pertinent, sans son URL. "\n'
       '           "Ne mentionne jamais de noms de fichiers.")')

assert old in s, "Prompt système introuvable — vérifier retriever.py"
s = s.replace(old, new)
with io.open(RET, "w", encoding="utf-8") as f:
    f.write(s)
print("   ✅ Le LLM ne générera plus de section Sources")
PYEOF
/opt/RAG-Gemini/venv/bin/python3 -m py_compile "$RET" && echo "   ✅ Syntaxe OK"

echo "2/3 — Synchronisation du widget VPS depuis le plugin WordPress..."
cp /opt/RAG-Gemini/static/rag-widget.js "/opt/RAG-Gemini/static/rag-widget.js.bak-$(date +%Y%m%d)" 2>/dev/null || true
curl -sf -o /opt/RAG-Gemini/static/rag-widget.js \
  "https://lhusser.fr/wp-content/plugins/rag-gemini-chat/assets/rag-widget.js?nocache=$(date +%s)"
grep -q "v2.0.1" /opt/RAG-Gemini/static/rag-widget.js \
  && echo "   ✅ Copie VPS = v2.0.1" \
  || echo "   ⚠️ Version inattendue — vérifier que le plugin v2.0.1 est bien actif sur WordPress"

echo "3/3 — Redémarrage..."
systemctl restart rag-gemini
sleep 3
systemctl is-active rag-gemini

echo ""
echo "✅ Terminé ! Ensuite côté WordPress :"
echo "   1. Purger LiteSpeed Cache (Purger tout)"
echo "   2. Tester en navigation privée — la section 'Sources :' texte doit avoir disparu,"
echo "      seules les cartes cliquables '📎 Sources consultées' restent."
