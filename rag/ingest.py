import os, io, logging
from pathlib import Path

logger = logging.getLogger(__name__)
CHUNK_SIZE=800; CHUNK_OVERLAP=100; FRAME_INTERVAL=5

def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    text=text.strip()
    if not text: return []
    chunks,start=[],0
    while start<len(text):
        chunks.append(text[start:start+size]); start+=size-overlap
    return chunks

def process_pdf(fp):
    try: import fitz
    except: logger.error("pymupdf manquant"); return
    src=Path(fp).name; doc=fitz.open(fp)
    for pn,page in enumerate(doc,1):
        txt=page.get_text("text").strip()
        if txt:
            for i,c in enumerate(chunk_text(txt)):
                yield {"type":"text","content":c,"metadata":{"source":src,"source_type":"pdf","page":pn,"chunk":i,"text":c}}
        for ii,ir in enumerate(page.get_images(full=True)):
            try:
                bi=doc.extract_image(ir[0]); cap=f"Image p{pn} — {src}"
                yield {"type":"image_bytes","content":bi["image"],"mime":f"image/{bi['ext']}","caption":cap,
                       "metadata":{"source":src,"source_type":"pdf_image","page":pn,"img_index":ii,"text":cap}}
            except: pass
    doc.close()

def process_image(fp):
    src=Path(fp).name; cap=f"Image : {src}"
    yield {"type":"image","content":fp,"caption":cap,"metadata":{"source":src,"source_type":"image","text":cap}}

def process_video(fp):
    src=Path(fp).name
    tr=_whisper(fp)
    if tr:
        for i,c in enumerate(chunk_text(tr)):
            yield {"type":"text","content":c,"metadata":{"source":src,"source_type":"video_transcript","chunk":i,"text":c}}
    try:
        from moviepy.editor import VideoFileClip
        from PIL import Image
        clip=VideoFileClip(fp); dur=clip.duration
        for t in range(0,int(dur),FRAME_INTERVAL):
            try:
                img=Image.fromarray(clip.get_frame(t))
                buf=io.BytesIO(); img.save(buf,format="JPEG",quality=75)
                m,s=divmod(int(t),60); ts=f"{m:02d}:{s:02d}"; cap=f"Frame {ts} — {src}"
                yield {"type":"image_bytes","content":buf.getvalue(),"mime":"image/jpeg","caption":cap,
                       "metadata":{"source":src,"source_type":"video_frame","timestamp":ts,"seconds":t,"text":cap}}
            except: pass
        clip.close()
    except ImportError: pass

def process_audio(fp):
    src=Path(fp).name; tr=_whisper(fp)
    if tr:
        for i,c in enumerate(chunk_text(tr)):
            yield {"type":"text","content":c,"metadata":{"source":src,"source_type":"audio","chunk":i,"text":c}}

def process_text(fp):
    src=Path(fp).name
    with open(fp,"r",encoding="utf-8",errors="ignore") as f: txt=f.read()
    # Détection auto d'un export WordPress (WXR) sauvegardé en .txt
    if "wordpress.org/export" in txt[:3000]:
        yield from process_wordpress_xml(fp); return
    for i,c in enumerate(chunk_text(txt)):
        yield {"type":"text","content":c,"metadata":{"source":src,"source_type":"text","chunk":i,"text":c}}

# ── WordPress WXR (export XML) ───────────────────────────────────
WXR_NS={"content":"http://purl.org/rss/1.0/modules/content/",
        "wp":"http://wordpress.org/export/1.2/",
        "excerpt":"http://wordpress.org/export/1.2/excerpt/",
        "dc":"http://purl.org/dc/elements/1.1/"}

def _html_to_text(html_str):
    """Convertit le HTML d'un article WordPress en texte brut (stdlib uniquement)."""
    from html.parser import HTMLParser
    import re
    class _P(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.parts=[]; self.skip=0
        def handle_starttag(self,tag,attrs):
            if tag in ("script","style"): self.skip+=1
            elif tag in ("p","br","div","li","h1","h2","h3","h4","h5","h6","tr","blockquote","figcaption"):
                self.parts.append("\n")
        def handle_endtag(self,tag):
            if tag in ("script","style") and self.skip>0: self.skip-=1
        def handle_data(self,data):
            if not self.skip: self.parts.append(data)
    # Supprimer les commentaires de blocs Gutenberg <!-- wp:... -->
    html_str=re.sub(r"<!--.*?-->","",html_str,flags=re.S)
    p=_P(); p.feed(html_str)
    txt="".join(p.parts)
    txt=re.sub(r"[ \t]+"," ",txt)
    txt=re.sub(r"\n{3,}","\n\n",txt)
    return txt.strip()

def process_wordpress_xml(fp):
    """Parse un export WordPress (WXR) et indexe les articles publiés."""
    import xml.etree.ElementTree as ET
    src=Path(fp).name
    try:
        tree=ET.parse(fp)
    except ET.ParseError as e:
        logger.error(f"XML invalide : {e}"); return
    nb=0
    for item in tree.getroot().iter("item"):
        post_type=(item.findtext("wp:post_type",default="",namespaces=WXR_NS) or "").strip()
        post_status=(item.findtext("wp:status",default="",namespaces=WXR_NS) or "").strip()
        if post_type!="post" or post_status!="publish": continue
        title=(item.findtext("title") or "Sans titre").strip()
        link=(item.findtext("link") or "").strip()
        date=(item.findtext("wp:post_date",default="",namespaces=WXR_NS) or "").strip()[:10]
        cats=[c.text.strip() for c in item.findall("category")
              if c.text and c.get("domain") in ("category","post_tag")]
        raw=item.findtext("content:encoded",default="",namespaces=WXR_NS) or ""
        body=_html_to_text(raw)
        if not body: continue
        header=f"Article : {title}\nDate : {date}\nURL : {link}\n"
        if cats: header+=f"Tags : {', '.join(cats[:10])}\n"
        for i,c in enumerate(chunk_text(body)):
            txt=header+"\n"+c if i==0 else f"[{title}] "+c
            yield {"type":"text","content":txt,
                   "metadata":{"source":src,"source_type":"wordpress_post","article":title,
                               "url":link,"date":date,"chunk":i,"text":txt}}
        nb+=1
    logger.info(f"WXR : {nb} articles publiés extraits de {src}")

def process_file(fp):
    ext=Path(fp).suffix.lower()
    if ext==".pdf": yield from process_pdf(fp)
    elif ext in {".jpg",".jpeg",".png",".gif",".webp",".bmp"}: yield from process_image(fp)
    elif ext in {".mp4",".mov",".avi",".mkv",".webm"}: yield from process_video(fp)
    elif ext in {".mp3",".wav",".m4a",".ogg",".flac"}: yield from process_audio(fp)
    elif ext in {".txt",".md",".csv"}: yield from process_text(fp)
    elif ext==".xml": yield from process_wordpress_xml(fp)
    else: logger.warning(f"Format non supporté : {ext}")

def _whisper(fp):
    try:
        import whisper; m=whisper.load_model("base")
        return m.transcribe(fp,fp16=False).get("text","").strip()
    except: return ""
