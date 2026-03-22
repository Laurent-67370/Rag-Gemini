import os, base64, logging
from pathlib import Path
from typing import Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-exp-03-07")
_client = None

def _get_client():
    global _client
    if not _client:
        _client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _client

def _embed(content, task="RETRIEVAL_DOCUMENT", retries=3):
    import time
    for i in range(retries):
        try:
            client = _get_client()
            if isinstance(content, str):
                result = client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=content,
                    config=types.EmbedContentConfig(task_type=task)
                )
            else:
                result = client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=content,
                    config=types.EmbedContentConfig(task_type=task)
                )
            return result.embeddings[0].values
        except Exception as e:
            logger.warning(f"Retry {i+1}: {e}")
            if i < retries-1: time.sleep(2**i)
    return None

def embed_text(text, task="RETRIEVAL_DOCUMENT"):
    return _embed(text, task) if text and text.strip() else None

def embed_image(path, caption=""):
    ext = Path(path).suffix.lower()
    mime = {"jpg":"image/jpeg","jpeg":"image/jpeg","png":"image/png","gif":"image/gif","webp":"image/webp"}.get(ext,"image/jpeg")
    with open(path,"rb") as f: data = f.read()
    parts = [types.Part.from_bytes(data=data, mime_type=mime)]
    if caption: parts.append(types.Part.from_text(text=caption))
    return _embed(parts)

def embed_image_bytes(data, mime="image/jpeg", caption=""):
    parts = [types.Part.from_bytes(data=data, mime_type=mime)]
    if caption: parts.append(types.Part.from_text(text=caption))
    return _embed(parts)

def embed_query(q):
    return embed_text(q, "RETRIEVAL_QUERY")
