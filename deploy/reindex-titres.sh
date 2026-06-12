#!/bin/bash
# reindex-titres.sh — Réindexe les articles dont le titre a changé dans WordPress
# Compare le titre WP actuel au titre stocké dans Pinecone : ne réingère que si différent.
set -e

/opt/RAG-Gemini/venv/bin/python3 << 'PYEOF'
# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, "/opt/RAG-Gemini")
from dotenv import load_dotenv
load_dotenv("/opt/RAG-Gemini/.env")
from bs4 import BeautifulSoup
from rag.wp_ingest import fetch_post, ingest_post
from rag.indexer import get_index

# Les 28 articles de la liste de corrections (prioritaires + optionnels)
IDS = [2979, 2933, 2860, 2690, 2677, 2669, 2663, 2660, 2657, 2625,
       2614, 2609, 2605, 2597, 2589, 2555, 2509, 2503, 2499, 2475,
       2457, 2076, 1993, 1823, 1748, 2821, 2819, 2755]

def indexed_title(pid):
    """Titre stocké dans Pinecone pour cet article (métadonnée 'article' du chunk 0)."""
    try:
        idx = get_index()
        res = idx.fetch(ids=["wp-%s-0" % pid])
        vecs = getattr(res, "vectors", None)
        if vecs is None and isinstance(res, dict):
            vecs = res.get("vectors", {})
        v = (vecs or {}).get("wp-%s-0" % pid)
        if v is None:
            return None
        meta = getattr(v, "metadata", None) or (v.get("metadata") if isinstance(v, dict) else {})
        return (meta or {}).get("article", "")
    except Exception as e:
        print("   ⚠️ Pinecone fetch %s : %s" % (pid, e))
        return None

maj, ok, err = 0, 0, 0
for i, pid in enumerate(IDS, 1):
    p = fetch_post(post_id=pid)
    if not p:
        print(f"({i}/{len(IDS)}) ❌ ID {pid} introuvable sur WordPress")
        err += 1
        continue
    wp_title = BeautifulSoup(p.get("title", {}).get("rendered", ""), "html.parser").get_text().strip()
    old = indexed_title(pid)
    if old is not None and old.strip() == wp_title:
        print(f"({i}/{len(IDS)}) ⏭️  ID {pid} déjà à jour — {wp_title[:55]}")
        ok += 1
        continue
    try:
        c = ingest_post(p)
        print(f"({i}/{len(IDS)}) ✅ ID {pid} réindexé ({c} chunks) — {wp_title[:55]}")
        maj += 1
    except Exception as e:
        print(f"({i}/{len(IDS)}) ❌ ID {pid} : {e}")
        err += 1

print(f"\n🎉 Terminé : {maj} réindexés · {ok} déjà à jour · {err} erreur(s)")
if err:
    print("⚠️  Relance le script pour retenter les erreurs (les articles à jour seront sautés).")
PYEOF
