#!/bin/bash
# fix-rate-limit.sh — Rate limiting renforcé pour RAG-Gemini
# Limites : 5/min/IP · 30/jour/IP · 400/jour global — sur /query ET /api/public-query
set -e
APP=/opt/RAG-Gemini/app.py

echo "1/4 — Sauvegarde..."
cp "$APP" "$APP.bak-rl-$(date +%Y%m%d-%H%M%S)"

echo "2/4 — Application du patch..."
python3 << 'PYEOF'
import io

APP = "/opt/RAG-Gemini/app.py"
with io.open(APP, encoding="utf-8") as f:
    s = f.read()

def rep(old, new):
    global s
    assert old in s, "INTROUVABLE : %s" % old[:60]
    assert s.count(old) == 1, "NON-UNIQUE : %s" % old[:60]
    s = s.replace(old, new)

# ── A. Nouveau limiteur à 3 niveaux + config ──────────────────────
rep('''_public_rl: dict = {}''',
'''_public_rl: dict = {}
_public_rl_day: dict = {}

import os as _os
RL_PER_MIN    = int(_os.environ.get("RAG_RL_PER_MIN", "5"))      # burst / minute / IP
RL_PER_DAY    = int(_os.environ.get("RAG_RL_PER_DAY", "30"))     # plafond / jour / IP
RL_GLOBAL_DAY = int(_os.environ.get("RAG_RL_GLOBAL_DAY", "400")) # plafond / jour global

def _rl_check(ip):
    """Retourne un message d'erreur si la limite est atteinte, sinon None."""
    import time
    now = time.time()
    if len(_public_rl) > 5000:  # purge anti-fuite mémoire
        _public_rl.clear(); _public_rl_day.clear()
    m = _public_rl.setdefault(ip, [])
    m[:] = [t for t in m if now - t < 60]
    d = _public_rl_day.setdefault(ip, [])
    d[:] = [t for t in d if now - t < 86400]
    g = _public_rl_day.setdefault("__global__", [])
    g[:] = [t for t in g if now - t < 86400]
    if len(m) >= RL_PER_MIN:
        return "Doucement ! Patiente une minute avant ta prochaine question. ⏳"
    if len(d) >= RL_PER_DAY:
        return "Tu as atteint la limite quotidienne de questions — reviens demain ! 🌙"
    if len(g) >= RL_GLOBAL_DAY:
        return "L'assistant a beaucoup discuté aujourd'hui — réessaie demain. 🌙"
    m.append(now); d.append(now); g.append(now)
    return None

def _rl_response(msg):
    # 'answer' + 'response' : le widget affiche le message tel quel
    return jsonify({"error": msg, "answer": msg, "response": msg, "sources": []}), 429''')

# ── B. /api/public-query : remplacer l'ancien limiteur ────────────
rep('''    import time
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?").split(",")[0].strip()
    now = time.time()
    hist = _public_rl.setdefault(ip, [])
    hist[:] = [t for t in hist if now - t < 60]
    if len(hist) >= 10:
        return jsonify({"error": "Trop de requêtes, patiente une minute."}), 429
    hist.append(now)''',
'''    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?").split(",")[0].strip()
    _rl_msg = _rl_check(ip)
    if _rl_msg:
        return _rl_response(_rl_msg)''')

# ── C. /query : ajouter le limiteur (absent jusqu'ici) ────────────
rep('''    if not _check_public_key():
        return jsonify({"error": "Clé API invalide"}), 401
    d = request.get_json(silent=True) or {}''',
'''    if not _check_public_key():
        return jsonify({"error": "Clé API invalide"}), 401
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?").split(",")[0].strip()
    _rl_msg = _rl_check(ip)
    if _rl_msg:
        return _rl_response(_rl_msg)
    d = request.get_json(silent=True) or {}''')

with io.open(APP, "w", encoding="utf-8") as f:
    f.write(s)
print("   ✅ 3 patchs appliqués")
PYEOF

echo "3/4 — Vérification syntaxe + redémarrage..."
python3 -m py_compile "$APP" && echo "   ✅ Syntaxe Python OK"
systemctl restart rag-gemini
sleep 3
systemctl is-active rag-gemini && echo "   ✅ Service redémarré"

echo "4/4 — Test du rate limit (questions vides = zéro coût API)..."
for i in 1 2 3 4 5 6 7; do
  code=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:5000/api/public-query \
    -H 'Content-Type: application/json' -d '{"question":""}')
  echo "   Requête $i → HTTP $code"
done
echo ""
echo "✅ Terminé ! Attendu : requêtes 1-5 → 400 (question vide), 6-7 → 429 (limite)."
echo "   Réglages modifiables : RAG_RL_PER_MIN / RAG_RL_PER_DAY / RAG_RL_GLOBAL_DAY"
