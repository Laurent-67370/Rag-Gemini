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
    for i,c in enumerate(chunk_text(txt)):
        yield {"type":"text","content":c,"metadata":{"source":src,"source_type":"text","chunk":i,"text":c}}

def process_file(fp):
    ext=Path(fp).suffix.lower()
    if ext==".pdf": yield from process_pdf(fp)
    elif ext in {".jpg",".jpeg",".png",".gif",".webp",".bmp"}: yield from process_image(fp)
    elif ext in {".mp4",".mov",".avi",".mkv",".webm"}: yield from process_video(fp)
    elif ext in {".mp3",".wav",".m4a",".ogg",".flac"}: yield from process_audio(fp)
    elif ext in {".txt",".md",".csv"}: yield from process_text(fp)
    else: logger.warning(f"Format non supporté : {ext}")

def _whisper(fp):
    try:
        import whisper; m=whisper.load_model("base")
        return m.transcribe(fp,fp16=False).get("text","").strip()
    except: return ""
