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
