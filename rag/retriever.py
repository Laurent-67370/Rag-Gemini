import os, logging
from typing import Optional
from dotenv import load_dotenv
from rag.embedder import embed_query, _get_client
from rag.indexer  import query_index
from google.genai import types

load_dotenv()
logger = logging.getLogger(__name__)
LLM_MODEL = os.getenv("GEMINI_LLM_MODEL", "gemini-2.5-flash")

def call_llm(sys_prompt, user_msg):
    try:
        client = _get_client()
        response = client.models.generate_content(
            model=LLM_MODEL,
            contents=user_msg,
            config=types.GenerateContentConfig(
                system_instruction=sys_prompt,
                temperature=0.2,
                max_output_tokens=1500,
            )
        )
        return response.text.strip()
    except Exception as e:
        return f"Erreur LLM : {e}"

def answer_question(question: str, top_k: int = 5,
                    source_filter: Optional[str] = None,
                    owner_filter: Optional[str] = None) -> dict:
    """
    Pipeline RAG avec filtre par source et/ou par propriétaire.
    owner_filter : seuls les vecteurs uploadés par cet user sont retournés (Option C).
    Admin (owner_filter=None) voit tout.
    """
    logger.info(f"Question: {question[:60]}… owner={owner_filter}")
    query_vec = embed_query(question)
    if not query_vec:
        return {"question": question, "answer": "Impossible de générer l'embedding.", "sources": []}

    # Construire le filtre Pinecone combiné
    filters = []
    if source_filter:
        filters.append({"source": {"$eq": source_filter}})
    if owner_filter:
        filters.append({"uploaded_by": {"$eq": owner_filter}})

    if len(filters) == 0:   filter_meta = None
    elif len(filters) == 1: filter_meta = filters[0]
    else:                   filter_meta = {"$and": filters}

    results = query_index(query_vec, top_k=top_k, filter_meta=filter_meta)

    if not results:
        msg = "Aucune information trouvée dans vos fichiers." if owner_filter else "Aucune information trouvée."
        return {"question": question, "answer": msg, "sources": []}

    parts = []; sources = []
    for r in results:
        m = r["metadata"]; ts = m.get("timestamp","")
        lbl = f"[{m.get('source_type','?').upper()}] {m.get('source','?')}{' @ '+ts if ts else ''} (score:{r['score']})"
        parts.append(f"{lbl}\n{m.get('text','')}")
        sources.append({"source":m.get("source","?"),"source_type":m.get("source_type","?"),
                        "score":r["score"],"text":m.get("text","")[:300],
                        "timestamp":ts,"vector_id":r["id"],
                        "owner":m.get("uploaded_by","—")})

    ctx = "\n\n---\n\n".join(parts)
    sys = "Tu es un assistant RAG multimodal. Réponds uniquement depuis le contexte fourni. Cite toujours la source. Réponds en français."
    usr = f"CONTEXTE :\n{ctx}\n\nQUESTION : {question}"
    return {"question": question, "answer": call_llm(sys, usr), "sources": sources}
