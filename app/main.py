"""VICE_0X Auto Shorts Bot: web server (batch 1).

Provides: password-protected mobile dashboard, creator-authorized video upload
with size/length/storage/daily limits, and a health check.
"""

import html
import logging
import re
import secrets
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote, urlparse

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.concurrency import run_in_threadpool

from app import limits
from app.config import APP_TITLE, BRAND_NAME, settings
from app.limits import LimitExceeded

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("vice0x")

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}
CHUNK_SIZE = 1024 * 1024  # 1 MB
SAFE_FILENAME = re.compile(r"^[A-Za-z0-9._-]{1,150}$")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    if not settings.dashboard_password:
        log.warning("DASHBOARD_PASSWORD is not set. The dashboard will stay locked.")
    yield


app = FastAPI(title=APP_TITLE, lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
security = HTTPBasic(auto_error=False)


# ---------------------------------------------------------------- security
def require_auth(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    if not settings.dashboard_password:
        raise HTTPException(
            status_code=503,
            detail="Dashboard locked: add the DASHBOARD_PASSWORD secret in your Space settings.",
        )
    if credentials is not None:
        user_ok = secrets.compare_digest(
            credentials.username.encode("utf-8"), settings.dashboard_user.encode("utf-8")
        )
        pass_ok = secrets.compare_digest(
            credentials.password.encode("utf-8"), settings.dashboard_password.encode("utf-8")
        )
        if user_ok and pass_ok:
            return credentials.username
    raise HTTPException(
        status_code=401,
        detail="Login required.",
        headers={"WWW-Authenticate": f'Basic realm="{BRAND_NAME}"'},
    )


def check_origin(request: Request) -> None:
    """Block form posts coming from other websites (basic CSRF protection)."""
    origin = request.headers.get("origin")
    if origin is None:
        return
    allowed = {
        request.headers.get("host", ""),
        request.headers.get("x-forwarded-host", ""),
    }
    if urlparse(origin).netloc not in allowed:
        raise HTTPException(status_code=403, detail="Cross-site request blocked.")


# ----------------------------------------------------------------- helpers
def redirect(message: str, level: str = "ok") -> RedirectResponse:
    return RedirectResponse(f"/?msg={quote(message)}&lvl={level}", status_code=303)


def list_uploads() -> list:
    folder = settings.uploads_dir
    if not folder.exists():
        return []
    files = [p for p in folder.iterdir() if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [{"name": p.name, "mb": round(p.stat().st_size / (1024 * 1024), 1)} for p in files]


# --------------------------------------------------------------------- UI
PAGE_CSS = """
:root{--bg:#0b0b10;--card:#16161f;--line:#2a2a38;--text:#f2f2f7;--mute:#9a9ab0;
--accent:#ff2d55;--ok:#2ecc71;--err:#ff5c5c}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);
font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;line-height:1.45}
header{padding:18px 16px;border-bottom:1px solid var(--line)}
h1{margin:0;font-size:1.25rem;letter-spacing:.5px}
h1 span{color:var(--accent)}
.sub{color:var(--mute);font-size:.85rem;margin-top:2px}
main{max-width:640px;margin:0 auto;padding:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;
padding:16px;margin-bottom:14px}
h2{margin:0 0 10px;font-size:1.05rem}
.msg{padding:12px 14px;border-radius:10px;margin-bottom:14px;font-size:.95rem}
.msg.ok{background:#12301f;border:1px solid var(--ok)}
.msg.error{background:#3a1616;border:1px solid var(--err)}
label{display:block;margin:10px 0 6px;color:var(--mute);font-size:.9rem}
input[type=file]{width:100%;padding:12px;background:#0f0f16;border:1px dashed var(--line);
border-radius:10px;color:var(--text)}
.check{display:flex;gap:10px;align-items:flex-start;margin:14px 0;color:var(--text);font-size:.9rem}
.check input{width:22px;height:22px;flex:none;margin-top:2px}
button{width:100%;padding:14px;border:0;border-radius:12px;background:var(--accent);
color:#fff;font-size:1rem;font-weight:600}
button.small{width:auto;padding:8px 12px;font-size:.85rem;background:#2a2a38}
.bar{height:8px;background:#0f0f16;border-radius:6px;overflow:hidden;margin:4px 0 12px}
.bar div{height:100%;background:var(--accent)}
.row{display:flex;justify-content:space-between;font-size:.9rem}
.file{display:flex;justify-content:space-between;align-items:center;gap:10px;
padding:10px 0;border-top:1px solid var(--line);font-size:.85rem;word-break:break-all}
.mute{color:var(--mute);font-size:.85rem}
"""


def render_page(message: str = "", level: str = "ok") -> str:
    msg_html = ""
    if message:
        css = "error" if level == "error" else "ok"
        msg_html = f'<div class="msg {css}">{html.escape(message)}</div>'

    usage_html = ""
    for row in limits.usage_snapshot():
        pct = 0 if not row["limit"] else min(100, round(100 * row["used"] / row["limit"]))
        usage_html += (
            f'<div class="row"><span>{html.escape(row["label"])}</span>'
            f'<span>{row["used"]} / {row["limit"]}</span></div>'
            f'<div class="bar"><div style="width:{pct}%"></div></div>'
        )

    files = list_uploads()
    if files:
        files_html = ""
        for f in files:
            name = html.escape(f["name"])
            files_html += (
                f'<div class="file"><span>{name}<br><span class="mute">{f["mb"]} MB</span></span>'
                f'<form method="post" action="/delete" '
                f'onsubmit="return confirm(\'Delete this video?\')">'
                f'<input type="hidden" name="name" value="{name}">'
                f'<button class="small" type="submit">Delete</button></form></div>'
            )
    else:
        files_html = '<p class="mute">No videos uploaded yet.</p>'

    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#0b0b10">
<title>{html.escape(APP_TITLE)}</title>
<style>{PAGE_CSS}</style></head>
<body>
<header>
  <h1>{html.escape(BRAND_NAME[:-2])}<span>{html.escape(BRAND_NAME[-2:])}</span> Auto Shorts Bot</h1>
  <div class="sub">Upload. Clip. Caption. Publish.</div>
</header>
<main>
  {msg_html}
  <div class="card">
    <h2>Upload a video</h2>
    <form method="post" action="/upload" enctype="multipart/form-data">
      <label for="video">Video file (MP4, MOV, MKV, WEBM, M4V)</label>
      <input id="video" type="file" name="video" accept="video/*" required>
      <p class="mute">Max {settings.max_upload_mb} MB and {settings.max_video_minutes} minutes per video.</p>
      <label class="check"><input type="checkbox" name="authorized" value="yes" required>
        <span>I created this video or have the creator's permission to use it for {html.escape(BRAND_NAME)}.</span></label>
      <button type="submit">Upload</button>
    </form>
  </div>
  <div class="card">
    <h2>Daily limits</h2>
    {usage_html}
    <p class="mute">Limits reset at midnight UTC. When a limit is hit, the bot stops instead of continuing.</p>
  </div>
  <div class="card">
    <h2>Your videos</h2>
    {files_html}
  </div>
  <div class="card">
    <h2>Status</h2>
    <p class="mute">Upload and limits: ready. Transcription, AI moments, clips, titles and YouTube publishing are added in the next batches.</p>
  </div>
</main>
</body></html>"""


# ------------------------------------------------------------------ routes
@app.get("/health")
async def health():
    """Public, no login. Shows only that the server is running."""
    return {"status": "ok", "app": BRAND_NAME}


@app.get("/", response_class=HTMLResponse)
async def dashboard(msg: str = "", lvl: str = "ok", _user: str = Depends(require_auth)):
    return HTMLResponse(render_page(msg[:300], lvl))


@app.get("/api/status")
async def api_status(_user: str = Depends(require_auth)):
    return JSONResponse(
        {
            "app": APP_TITLE,
            "usage": limits.usage_snapshot(),
            "videos": list_uploads(),
        }
    )


@app.post("/upload")
async def upload(
    request: Request,
    video: UploadFile = File(...),
    authorized: str = Form(None),
    _user: str = Depends(require_auth),
):
    check_origin(request)

    if authorized != "yes":
        return redirect("Please confirm you have permission to use this video.", "error")

    ext = Path(video.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        return redirect(f"Unsupported file type. Allowed: {allowed}", "error")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > max_bytes + CHUNK_SIZE:
        return redirect(f"File is too large. Maximum is {settings.max_upload_mb} MB.", "error")

    try:
        limits.consume("uploads")
    except LimitExceeded as exc:
        return redirect(str(exc), "error")

    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(video.filename or "").stem)[:60] or "video"
    dest = settings.uploads_dir / f"{stem}_{uuid.uuid4().hex[:8]}{ext}"
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)

    room = limits.storage_room_bytes()
    success = False
    message = "Upload failed. Please try again."
    try:
        written = 0
        with dest.open("wb") as out:
            while True:
                chunk = await video.read(CHUNK_SIZE)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    raise LimitExceeded(f"File is too large. Maximum is {settings.max_upload_mb} MB.")
                if written > room:
                    raise LimitExceeded("Server storage limit reached. Delete old videos first.")
                out.write(chunk)

        duration = await run_in_threadpool(limits.probe_duration_seconds, dest)
        if duration is not None and duration > settings.max_video_minutes * 60:
            raise LimitExceeded(
                f"Video is {duration / 60:.1f} minutes. Maximum is {settings.max_video_minutes} minutes."
            )
        success = True
        message = f"Uploaded {dest.name}"
        if duration is None:
            message += " (length check skipped: ffprobe not installed here)"
    except LimitExceeded as exc:
        message = str(exc)
    except Exception:
        log.exception("Upload error")
    finally:
        await video.close()
        if not success:
            dest.unlink(missing_ok=True)
            limits.refund("uploads")

    return redirect(message, "ok" if success else "error")


@app.post("/delete")
async def delete_video(
    request: Request,
    name: str = Form(...),
    _user: str = Depends(require_auth),
):
    check_origin(request)
    if not SAFE_FILENAME.match(name):
        return redirect("Invalid file name.", "error")
    target = (settings.uploads_dir / name).resolve()
    if target.parent != settings.uploads_dir.resolve() or not target.is_file():
        return redirect("File not found.", "error")
    target.unlink()
    return redirect(f"Deleted {name}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=7860)
