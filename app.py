import os, logging, threading, uuid, hashlib, json
from pathlib import Path
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, session, redirect
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

UPLOAD_ROOT = Path("uploads")
FOLDERS = {"videos": UPLOAD_ROOT/"videos", "images": UPLOAD_ROOT/"images", "texte": UPLOAD_ROOT/"texte"}
for f in FOLDERS.values(): f.mkdir(parents=True, exist_ok=True)

ALLOWED = {".mp4",".mov",".avi",".mkv",".webm",".jpg",".jpeg",".png",".gif",".webp",".bmp",
           ".pdf",".txt",".md",".csv",".mp3",".wav",".m4a",".xml"}
EXT_FOLDER = {
    **{e:"videos" for e in [".mp4",".mov",".avi",".mkv",".webm"]},
    **{e:"images" for e in [".jpg",".jpeg",".png",".gif",".webp",".bmp"]},
    **{e:"texte"  for e in [".pdf",".txt",".md",".csv",".mp3",".wav",".m4a",".xml"]},
}

ENV_FILE = "/opt/RAG-Gemini/.env"
USERS_FILE = Path("/opt/RAG-Gemini/users.json")

def _hash(p): return hashlib.sha256(p.encode()).hexdigest()

def load_users():
    if USERS_FILE.exists(): return json.loads(USERS_FILE.read_text())
    default = {
        "laurent": {"password":_hash("Laurent2026"),"role":"admin","color":"#f97316"},
        "ami":     {"password":_hash("Ami2026"),    "role":"user", "color":"#60a5fa"},
    }
    USERS_FILE.write_text(json.dumps(default,indent=2))
    return default

def save_users(u): USERS_FILE.write_text(json.dumps(u,indent=2))

app = Flask(__name__, static_folder="static")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "rag-gemini-secret-change-me-2026")
from datetime import timedelta
app.permanent_session_lifetime = timedelta(days=7)
CORS(app, supports_credentials=True)
status: dict = {}

def login_required(f):
    @wraps(f)
    def decorated(*args,**kwargs):
        if not session.get("user"):
            return jsonify({"error":"Non authentifié","redirect":"/login"}),401
        return f(*args,**kwargs)
    return decorated

# ── AUTH ─────────────────────────────────────────────────────────
@app.route("/login")
def login_page():
    p=Path("static/login.html")
    return p.read_text() if p.exists() else "<h1>Login page missing</h1>"

@app.route("/api/login", methods=["POST"])
def api_login():
    d=request.get_json() or {}
    username=d.get("username","").strip().lower()
    password=d.get("password","")
    users=load_users()
    user=users.get(username)
    if not user or user["password"]!=_hash(password):
        return jsonify({"error":"Identifiants incorrects"}),401
    session.permanent=True
    session["user"]=username; session["role"]=user.get("role","user"); session["color"]=user.get("color","#f97316")
    return jsonify({"message":"Connecté","user":username,"role":user.get("role"),"color":user.get("color")})

@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"message":"Déconnecté"})

@app.route("/api/me")
def api_me():
    if not session.get("user"): return jsonify({"authenticated":False}),401
    return jsonify({"authenticated":True,"user":session["user"],"role":session.get("role","user"),"color":session.get("color","#f97316")})

@app.route("/api/users", methods=["GET"])
@login_required
def api_users():
    if session.get("role")!="admin": return jsonify({"error":"Accès refusé"}),403
    users=load_users()
    return jsonify({"users":[{"username":u,"role":v["role"],"color":v["color"]} for u,v in users.items()]})

@app.route("/api/users", methods=["POST"])
@login_required
def api_add_user():
    if session.get("role")!="admin": return jsonify({"error":"Accès refusé"}),403
    d=request.get_json() or {}
    username=d.get("username","").strip().lower(); password=d.get("password","")
    role=d.get("role","user"); color=d.get("color","#60a5fa")
    if not username or not password: return jsonify({"error":"Username et password requis"}),400
    users=load_users(); users[username]={"password":_hash(password),"role":role,"color":color}
    save_users(users)
    return jsonify({"message":f"Utilisateur '{username}' créé."})

@app.route("/api/users/<username>", methods=["DELETE"])
@login_required
def api_del_user(username):
    if session.get("role")!="admin": return jsonify({"error":"Accès refusé"}),403
    if username==session.get("user"): return jsonify({"error":"Impossible de supprimer son propre compte"}),400
    users=load_users()
    if username not in users: return jsonify({"error":"Introuvable"}),404
    del users[username]; save_users(users)
    return jsonify({"message":f"'{username}' supprimé."})

@app.route("/api/change-password", methods=["POST"])
@login_required
def api_change_password():
    d=request.get_json() or {}
    old_pw=d.get("old_password",""); new_pw=d.get("new_password","")
    if not new_pw or len(new_pw)<4: return jsonify({"error":"Mot de passe trop court"}),400
    users=load_users(); username=session["user"]
    if users[username]["password"]!=_hash(old_pw): return jsonify({"error":"Ancien mot de passe incorrect"}),401
    users[username]["password"]=_hash(new_pw); save_users(users)
    return jsonify({"message":"Mot de passe mis à jour."})

# ── RAG ──────────────────────────────────────────────────────────
def ingest_async(filepath, name, owner):
    from rag.embedder import embed_text, embed_image, embed_image_bytes
    from rag.indexer  import upsert_batch
    from rag.ingest   import process_file
    status[name]={"status":"processing","progress":0,"total":0,"error":None,"owner":owner}
    try:
        # Mise à jour : purge les anciens vecteurs de ce fichier avant ré-indexation
        try:
            from rag.indexer import delete_vectors_by_source
            delete_vectors_by_source(name)
        except Exception as e:
            logger.warning(f"Purge ancienne version impossible : {e}")
        chunks=list(process_file(filepath)); status[name]["total"]=len(chunks)
        if not chunks: status[name].update({"status":"error","error":"Aucun contenu extrait."}); return
        batch=[]; done=0
        for c in chunks:
            emb=None; t=c["type"]
            if t=="text": emb=embed_text(c["content"])
            elif t=="image": emb=embed_image(c["content"],c.get("caption",""))
            elif t=="image_bytes": emb=embed_image_bytes(c["content"],c.get("mime","image/jpeg"),c.get("caption",""))
            if emb:
                c["metadata"]["uploaded_by"]=owner
                batch.append({"id":str(uuid.uuid4()),"values":emb,"metadata":c["metadata"]})
            done+=1; status[name]["progress"]=done
            if len(batch)>=50: upsert_batch(batch); batch=[]
        if batch: upsert_batch(batch)
        status[name]["status"]="done"
    except Exception as e:
        status[name].update({"status":"error","error":str(e)}); logger.error(e)

@app.route("/api/upload", methods=["POST"])
@login_required
def upload():
    f=request.files.get("file")
    if not f or not f.filename: return jsonify({"error":"Fichier manquant"}),400
    fn=secure_filename(f.filename); ext=Path(fn).suffix.lower()
    if ext not in ALLOWED: return jsonify({"error":f"Format non supporté : {ext}"}),400
    folder=FOLDERS[EXT_FOLDER.get(ext,"texte")]; path=folder/fn; f.save(str(path))
    threading.Thread(target=ingest_async,args=(str(path),fn,session.get("user","?")),daemon=True).start()
    return jsonify({"message":f"'{fn}' uploadé","filename":fn})

@app.route("/api/ingestion-status/<fn>")
@login_required
def ingest_status(fn): return jsonify(status.get(fn,{"status":"unknown"}))

@app.route("/api/query", methods=["POST"])
@login_required
def query():
    d=request.get_json(); q=(d or {}).get("question","").strip(); src=(d or {}).get("source_filter",None)
    if not q: return jsonify({"error":"Question vide"}),400
    from rag.retriever import answer_question
    # Option C : filtre par propriétaire sauf pour l'admin
    owner = None if session.get("role") == "admin" else session.get("user")
    result = answer_question(q, source_filter=src, owner_filter=owner)
    result["asked_by"] = session.get("user")
    return jsonify(result)

@app.route("/api/stats")
@login_required
def stats():
    from rag.indexer import get_index_stats; return jsonify(get_index_stats())

@app.route("/api/files")
@login_required
def files():
    out=[]
    current_user = session.get("user")
    is_admin = session.get("role") == "admin"
    for fn,fp in FOLDERS.items():
        for f in fp.iterdir():
            if f.is_file():
                s=status.get(f.name,{})
                file_owner = s.get("owner","—")
                # Option C : non-admin voit seulement ses propres fichiers
                if not is_admin and file_owner != current_user:
                    continue
                out.append({"name":f.name,"folder":fn,"size_kb":round(f.stat().st_size/1024,1),
                            "ext":f.suffix.lower(),"status":s.get("status","unknown"),"owner":file_owner})
    return jsonify({"files":out})

@app.route("/api/delete/<fn>", methods=["DELETE"])
@login_required
def delete(fn):
    fn=secure_filename(fn)
    file_owner=status.get(fn,{}).get("owner","—")
    if session.get("role")!="admin" and file_owner!=session.get("user"):
        return jsonify({"error":"Seul l'admin ou le propriétaire peut supprimer"}),403
    for fp in FOLDERS.values():
        p=fp/fn
        if p.exists():
            p.unlink()
            from rag.indexer import delete_vectors_by_source; delete_vectors_by_source(fn)
            status.pop(fn,None); return jsonify({"message":f"'{fn}' supprimé."})
    return jsonify({"error":"Introuvable"}),404

@app.route("/api/clear", methods=["DELETE"])
@login_required
def clear_all():
    if session.get("role")!="admin": return jsonify({"error":"Réservé à l'admin"}),403
    try:
        from rag.indexer import get_index; get_index().delete(delete_all=True); status.clear()
        return jsonify({"message":"Base vidée."})
    except Exception as e: return jsonify({"error":str(e)}),500

@app.route("/api/vectors")
@login_required
def get_vectors():
    try:
        from rag.indexer import get_index
        idx=get_index(); total=idx.describe_index_stats().get("total_vector_count",0)
        if total==0: return jsonify({"vectors":[],"total":0})
        import random; dim=int(os.getenv("EMBEDDING_DIMENSION","3072"))
        dummy=[random.gauss(0,.1) for _ in range(dim)]
        # Option C : filtre par owner pour non-admin
        is_admin = session.get("role") == "admin"
        owner_f = None if is_admin else {"uploaded_by": {"$eq": session.get("user")}}
        result=idx.query(vector=dummy,top_k=min(80,total),include_metadata=True,filter=owner_f)
        vectors=[{"id":m["id"],"score":m["score"],"source":m.get("metadata",{}).get("source","?"),
                  "source_type":m.get("metadata",{}).get("source_type","?"),
                  "text":m.get("metadata",{}).get("text","")[:80],
                  "page":m.get("metadata",{}).get("page",""),
                  "timestamp":m.get("metadata",{}).get("timestamp",""),
                  "owner":m.get("metadata",{}).get("uploaded_by","—")} for m in result.get("matches",[])]
        return jsonify({"vectors":vectors,"total":total})
    except Exception as e: return jsonify({"error":str(e),"vectors":[],"total":0}),500

@app.route("/api/config", methods=["GET"])
@login_required
def get_config():
    return jsonify({"gemini_embedding_model":os.getenv("GEMINI_EMBEDDING_MODEL","models/gemini-embedding-2-preview"),
                    "gemini_llm_model":os.getenv("GEMINI_LLM_MODEL","gemini-2.5-flash"),
                    "openrouter_model":os.getenv("OPENROUTER_MODEL",""),
                    "pinecone_index":os.getenv("PINECONE_INDEX_NAME","rag-multimodal"),
                    "embedding_dimension":os.getenv("EMBEDDING_DIMENSION","3072")})

@app.route("/api/config", methods=["POST"])
@login_required
def update_config():
    if session.get("role")!="admin": return jsonify({"error":"Réservé à l'admin"}),403
    d=request.get_json() or {}
    mapping={"gemini_llm_model":"GEMINI_LLM_MODEL","openrouter_model":"OPENROUTER_MODEL","gemini_embedding_model":"GEMINI_EMBEDDING_MODEL"}
    updated=[]
    for key,env_key in mapping.items():
        if key in d and d[key].strip():
            try:
                lines=open(ENV_FILE).readlines(); new_lines=[]; found=False
                for line in lines:
                    if line.startswith(env_key+'='): new_lines.append(f"{env_key}={d[key].strip()}\n"); found=True
                    else: new_lines.append(line)
                if not found: new_lines.append(f"{env_key}={d[key].strip()}\n")
                open(ENV_FILE,'w').writelines(new_lines)
            except: pass
            os.environ[env_key]=d[key].strip(); updated.append(env_key)
    return jsonify({"message":f"Mis à jour : {', '.join(updated)}","updated":updated})

@app.route("/api/preview/<folder>/<filename>")
@login_required
def preview_file(folder,filename):
    filename=secure_filename(filename); folder_path=FOLDERS.get(folder)
    if not folder_path: return jsonify({"error":"Dossier invalide"}),404
    return send_from_directory(str(folder_path),filename)

# ── ENDPOINT PUBLIC (widget blog lhusser.fr) ─────────────────────
RAG_PUBLIC_API_KEY = os.getenv("RAG_PUBLIC_API_KEY", "")

def _check_public_key():
    return RAG_PUBLIC_API_KEY and request.headers.get("x-api-key", "") == RAG_PUBLIC_API_KEY

@app.route("/health")
def public_health():
    return jsonify({"status": "ok", "service": "rag-gemini"})

@app.route("/stats", methods=["GET"])
def public_stats():
    """Stats publiques pour le widget (compteur + statut en ligne)."""
    if not _check_public_key():
        return jsonify({"error": "Clé API invalide"}), 401
    try:
        from rag.indexer import get_index
        total = get_index().describe_index_stats().get("total_vector_count", 0)
    except Exception:
        total = 0
    return jsonify({"articles_indexed": total, "vectors": total, "status": "ok"})

@app.route("/query", methods=["POST", "OPTIONS"])
def public_query():
    if request.method == "OPTIONS":
        return ("", 204)
    if not RAG_PUBLIC_API_KEY:
        return jsonify({"error": "Endpoint public désactivé (RAG_PUBLIC_API_KEY manquant)"}), 503
    if not _check_public_key():
        return jsonify({"error": "Clé API invalide"}), 401
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?").split(",")[0].strip()
    _rl_msg = _rl_check(ip)
    if _rl_msg:
        return _rl_response(_rl_msg)
    d = request.get_json(silent=True) or {}
    q = d.get("question", "").strip()
    if not q:
        return jsonify({"error": "Question vide"}), 400
    mode = d.get("mode", "chat")
    top_k = min(int(d.get("n_results", 5) or 5), 10)
    from rag.retriever import answer_question
    result = answer_question(q, top_k=top_k, source_filter="lhusser.fr")
    if mode == "search":
        # Mode recherche : liste de résultats sans appel LLM affiché
        return jsonify({"results": [{"title": s.get("title", s.get("source", "?")),
                                     "url": s.get("url", ""),
                                     "excerpt": s.get("text", ""),
                                     "score": s.get("score", 0)}
                                    for s in result.get("sources", [])]})
    result["response"] = result.get("answer", "")  # alias compatibilité widget
    return jsonify(result)

@app.route("/api/public-query", methods=["POST", "OPTIONS"])
def api_public_query():
    """Endpoint du plugin WordPress 'RAG Gemini Chat' (sans clé API).
    Protégé par un rate limit simple par IP pour limiter l'abus."""
    if request.method == "OPTIONS":
        return ("", 204)
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?").split(",")[0].strip()
    _rl_msg = _rl_check(ip)
    if _rl_msg:
        return _rl_response(_rl_msg)
    d = request.get_json(silent=True) or {}
    q = d.get("question", "").strip()[:500]
    if not q:
        return jsonify({"error": "Question vide"}), 400
    top_k = min(int(d.get("n_results", 5) or 5), 8)
    from rag.retriever import answer_question
    result = answer_question(q, top_k=top_k, source_filter="lhusser.fr")
    # Déduplication par article (les chunks d'un même article = une seule puce)
    seen = set(); uniq = []
    for s in result.get("sources", []):
        k = s.get("url") or s.get("title") or s.get("source")
        if k in seen: continue
        seen.add(k); uniq.append(s)
    result["sources"] = uniq
    # Le widget affiche le champ "source" : on y met le titre de l'article
    for s in result.get("sources", []):
        if s.get("title") and s.get("url"):
            s["source"] = s["title"]
    result["response"] = result.get("answer", "")
    return jsonify(result)

_public_rl: dict = {}
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
    return jsonify({"error": msg, "answer": msg, "response": msg, "sources": []}), 429

@app.route("/api/ingest-article", methods=["POST"])
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

_articles_cache = {"t": 0, "data": []}

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

@app.route("/api/sync-latest", methods=["POST"])
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

@app.route("/")
def index():
    if not session.get("user"): return redirect("/login")
    p=Path("static/index.html")
    return p.read_text() if p.exists() else "<h1>Interface non trouvée</h1>"

if __name__=="__main__":
    port=int(os.getenv("FLASK_PORT",5000))
    logger.info(f"🚀 http://0.0.0.0:{port}")
    app.run(host="0.0.0.0",port=port,debug=False)
