import os, logging, uuid
from typing import Optional
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME","rag-multimodal")
DIMENSION  = int(os.getenv("EMBEDDING_DIMENSION","3072"))
_pc = _index = None

def _client():
    global _pc
    if not _pc: _pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    return _pc

def get_index():
    global _index
    if _index: return _index
    pc = _client()
    if INDEX_NAME not in [i.name for i in pc.list_indexes()]:
        pc.create_index(name=INDEX_NAME, dimension=DIMENSION, metric="cosine",
                        spec=ServerlessSpec(cloud="aws", region="us-east-1"))
    _index = pc.Index(INDEX_NAME)
    return _index

def upsert_vector(emb, meta, vid=None):
    idx = get_index(); vid = vid or str(uuid.uuid4())
    if "text" in meta and len(meta["text"])>1000: meta["text"]=meta["text"][:1000]+"…"
    idx.upsert(vectors=[{"id":vid,"values":emb,"metadata":meta}])
    return vid

def upsert_batch(vectors):
    if not vectors: return 0
    idx = get_index(); total=0
    for i in range(0,len(vectors),100):
        idx.upsert(vectors=vectors[i:i+100]); total+=len(vectors[i:i+100])
    return total

def query_index(qvec, top_k=5, filter_meta=None):
    kw = {"vector":qvec,"top_k":top_k,"include_metadata":True}
    if filter_meta: kw["filter"]=filter_meta
    return [{"id":m["id"],"score":round(m["score"],4),"metadata":m.get("metadata",{})}
            for m in get_index().query(**kw).get("matches",[])]

def get_index_stats():
    try:
        s = get_index().describe_index_stats()
        return {"total_vectors":s.get("total_vector_count",0),"dimension":DIMENSION,"index_name":INDEX_NAME}
    except: return {"total_vectors":0,"dimension":DIMENSION,"index_name":INDEX_NAME}

def delete_vectors_by_source(src):
    try: get_index().delete(filter={"source":{"$eq":src}}); return True
    except: return False
