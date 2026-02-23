from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

BASE_DIR = Path(__file__).resolve().parent
RECORDINGS_DIR = BASE_DIR / "recordings"
DB_PATH = BASE_DIR / "surveillance.db"
RECORDINGS_DIR.mkdir(exist_ok=True)


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                details TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recordings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                duration_seconds REAL,
                size_bytes INTEGER,
                created_at TEXT NOT NULL
            )
            """
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Smart Surveillance App", version="2.0.1", lifespan=lifespan)


def log_event(event_type: str, details: str = "") -> None:
    with _db() as conn:
        conn.execute(
            "INSERT INTO events(event_type, details, created_at) VALUES (?, ?, ?)",
            (event_type, details, datetime.utcnow().isoformat()),
        )


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Application de Surveillance</title>
  <style>
    :root {{
      --bg: #0b1020; --panel: #151b2f; --accent: #6d8cff; --danger: #ff5d73;
      --ok: #3ddc97; --text: #eef3ff; --muted: #a3b1d1;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; font-family: Inter, Segoe UI, Arial, sans-serif; background: radial-gradient(circle at top right, #1b2342, var(--bg)); color: var(--text); min-height: 100vh; }}
    .container {{ max-width: 1280px; margin: 0 auto; padding: 24px; }}
    .header {{ display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:16px; margin-bottom:20px; }}
    h1 {{ margin:0; }} .muted {{ color: var(--muted); }}
    .layout {{ display:grid; grid-template-columns: 2fr 1fr; gap:20px; }}
    @media (max-width: 1000px) {{ .layout {{ grid-template-columns: 1fr; }} }}
    .panel {{ background: linear-gradient(145deg, #161d35, var(--panel)); border: 1px solid #2a355f; border-radius: 16px; padding: 16px; }}
    .video-wrap {{ position: relative; width: 100%; border-radius: 12px; overflow: hidden; border: 1px solid #2f3b69; background: #0b1020; aspect-ratio: 16/9; }}
    video, canvas {{ position:absolute; inset:0; width:100%; height:100%; object-fit:cover; }}
    .badge {{ display:inline-block; padding:6px 10px; border-radius:999px; font-size:.85rem; font-weight:600; margin-right:6px; background:#263260; border:1px solid #3a4c8f; }}
    .badge.ok {{ border-color:#2a7f61; background:#144435; }} .badge.danger {{ border-color:#8d2f44; background:#4d1b28; }}
    .controls {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:10px; margin-top:14px; }}
    button, select {{ width:100%; border:1px solid #3a4c8f; background:#1f2a4f; color:var(--text); border-radius:10px; padding:11px 12px; cursor:pointer; font-weight:600; }}
    button.primary {{ background: linear-gradient(90deg, #4464ff, var(--accent)); }}
    button.stop {{ background: linear-gradient(90deg, #ff5370, var(--danger)); border-color: #a33a4f; }}
    .stats {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:12px; }}
    .card {{ background:#0f162d; border:1px solid #293764; border-radius:10px; padding:10px; }}
    .card h3 {{ margin:0 0 4px; font-size:.9rem; color:var(--muted); font-weight:500; }}
    .card p {{ margin:0; font-size:1.2rem; font-weight:700; }}
    .db-table {{ margin-top:12px; max-height:320px; overflow:auto; border:1px solid #27345d; border-radius:10px; }}
    table {{ width:100%; border-collapse: collapse; }} th, td {{ border-bottom:1px solid #27345d; padding:8px; font-size:.86rem; text-align:left; }}
    th {{ background:#101833; position:sticky; top:0; }}
    .log {{ margin-top:12px; max-height:220px; overflow:auto; background:#0d1428; border:1px solid #27345d; border-radius:10px; padding:10px; font-size:.9rem; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div>
        <h1>🛡️ Application de Surveillance Complète</h1>
        <p class="muted">Caméra locale (PC / téléphone), enregistrement, suivi, base de données des événements.</p>
      </div>
      <div>
        <span class="badge">Généré: {generated_at}</span>
        <span id="cameraStatus" class="badge">Caméra arrêtée</span>
        <span id="trackingStatus" class="badge">Suivi OFF</span>
      </div>
    </div>

    <div class="layout">
      <div class="panel">
        <div class="video-wrap">
          <video id="video" playsinline autoplay muted></video>
          <canvas id="overlay"></canvas>
        </div>
        <div class="controls">
          <select id="cameraSelect"></select>
          <button id="startBtn" class="primary">▶️ Activer vidéo</button>
          <button id="stopBtn" class="stop">⏹️ Arrêter vidéo</button>
          <button id="recordBtn">⏺️ Démarrer enregistrement</button>
          <button id="trackBtn">🎯 Activer suivi</button>
          <button id="snapshotBtn">📸 Capture image</button>
          <button id="refreshDbBtn">🗃️ Rafraîchir base</button>
        </div>
      </div>

      <div class="panel">
        <h2 style="margin-top:0">État</h2>
        <div class="stats">
          <div class="card"><h3>Mode</h3><p id="modeLabel">Inactif</p></div>
          <div class="card"><h3>Enregistrement</h3><p id="recordingLabel">Non</p></div>
          <div class="card"><h3>Mouvements détectés</h3><p id="motionCount">0</p></div>
          <div class="card"><h3>Caméra</h3><p id="cameraName">-</p></div>
        </div>
        <div class="log" id="log"></div>
      </div>
    </div>

    <div class="panel" style="margin-top:20px;">
      <h2 style="margin-top:0">Base de données de surveillance</h2>
      <p class="muted">Historique persistant dans SQLite.</p>
      <div class="db-table">
        <table>
          <thead><tr><th>ID</th><th>Type</th><th>Détails</th><th>Date</th></tr></thead>
          <tbody id="eventsTable"></tbody>
        </table>
      </div>
    </div>
  </div>

<script>
const video = document.getElementById('video');
const overlay = document.getElementById('overlay');
const ctx = overlay.getContext('2d');
const cameraSelect = document.getElementById('cameraSelect');
const cameraStatus = document.getElementById('cameraStatus');
const trackingStatus = document.getElementById('trackingStatus');
const modeLabel = document.getElementById('modeLabel');
const recordingLabel = document.getElementById('recordingLabel');
const motionCountEl = document.getElementById('motionCount');
const cameraNameEl = document.getElementById('cameraName');
const eventsTable = document.getElementById('eventsTable');
const logEl = document.getElementById('log');

let stream = null; let mediaRecorder = null; let recordedChunks = [];
let trackingEnabled = false; let motionCount = 0; let animationId = null; let prevFrame = null;

function log(message) {{
  const p = document.createElement('p');
  p.textContent = `[${{new Date().toLocaleTimeString()}}] ${{message}}`;
  logEl.prepend(p);
}}

async function persistEvent(eventType, details='') {{
  await fetch('/api/events', {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify({{ event_type: eventType, details }})
  }});
}}

async function loadEvents() {{
  const res = await fetch('/api/events?limit=80');
  const data = await res.json();
  eventsTable.innerHTML = '';
  data.events.forEach(e => {{
    eventsTable.innerHTML += `<tr><td>${{e.id}}</td><td>${{e.event_type}}</td><td>${{e.details || ''}}</td><td>${{e.created_at}}</td></tr>`;
  }});
}}

function setBadge(el, text, state='') {{
  el.textContent = text;
  el.className = state ? `badge ${{state}}` : 'badge';
}}

async function listCameras() {{
  const devices = await navigator.mediaDevices.enumerateDevices();
  const cams = devices.filter(d => d.kind === 'videoinput');
  cameraSelect.innerHTML = '';
  cams.forEach((cam, i) => {{
    const op = document.createElement('option');
    op.value = cam.deviceId; op.textContent = cam.label || `Caméra ${{i+1}}`;
    cameraSelect.appendChild(op);
  }});
}}

async function startCamera() {{
  try {{
    if (stream) stopCamera();
    const selected = cameraSelect.value;
    const constraints = selected ? {{ video: {{ deviceId: {{ exact: selected }} }}, audio:false }} : {{ video:true, audio:false }};
    stream = await navigator.mediaDevices.getUserMedia(constraints);
    video.srcObject = stream;
    const track = stream.getVideoTracks()[0];
    cameraNameEl.textContent = track.label || 'Caméra active';
    modeLabel.textContent = 'Surveillance';
    setBadge(cameraStatus, 'Caméra active', 'ok');
    await persistEvent('camera_start', cameraNameEl.textContent);
    await loadEvents();
    log('Caméra démarrée');
    await new Promise(r => video.onloadedmetadata = r);
    overlay.width = video.videoWidth; overlay.height = video.videoHeight;
    drawLoop();
  }} catch (err) {{
    log('Erreur caméra: ' + err.message);
    setBadge(cameraStatus, 'Erreur caméra', 'danger');
  }}
}}

async function stopCamera() {{
  if (animationId) cancelAnimationFrame(animationId);
  if (stream) stream.getTracks().forEach(t => t.stop());
  stream = null; video.srcObject = null; prevFrame = null;
  ctx.clearRect(0, 0, overlay.width, overlay.height);
  modeLabel.textContent = 'Inactif'; cameraNameEl.textContent='-';
  setBadge(cameraStatus, 'Caméra arrêtée');
  await persistEvent('camera_stop');
  await loadEvents();
  log('Caméra arrêtée');
}}

async function startRecording() {{
  if (!stream) {{ log("Démarre la caméra d'abord."); return; }}
  recordedChunks = [];
  mediaRecorder = new MediaRecorder(stream, {{ mimeType: 'video/webm' }});
  const startedAt = Date.now();
  mediaRecorder.ondataavailable = e => {{ if (e.data.size > 0) recordedChunks.push(e.data); }};
  mediaRecorder.onstop = async () => {{
    const blob = new Blob(recordedChunks, {{ type:'video/webm' }});
    const duration = (Date.now()-startedAt)/1000;
    const filename = `surveillance_${{new Date().toISOString().replace(/[:.]/g, '-')}}.webm`;
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = filename; a.click(); URL.revokeObjectURL(url);
    await fetch('/api/recordings', {{
      method: 'POST', headers: {{ 'Content-Type':'application/json' }},
      body: JSON.stringify({{ filename, duration_seconds: duration, size_bytes: blob.size }})
    }});
    await persistEvent('recording_saved', `${{filename}} (${{Math.round(duration)}}s)`);
    await loadEvents();
    log('Enregistrement sauvegardé');
  }};
  mediaRecorder.start();
  recordingLabel.textContent = 'Oui';
  await persistEvent('recording_start');
  await loadEvents();
  log('Enregistrement démarré');
}}

async function stopRecording() {{
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {{
    mediaRecorder.stop();
    recordingLabel.textContent = 'Non';
    await persistEvent('recording_stop');
    await loadEvents();
    log('Enregistrement arrêté');
  }}
}}

async function toggleTracking() {{
  trackingEnabled = !trackingEnabled;
  if (trackingEnabled) {{
    setBadge(trackingStatus, 'Suivi ON', 'ok');
    await persistEvent('tracking_on');
    log('Suivi activé');
  }} else {{
    setBadge(trackingStatus, 'Suivi OFF');
    await persistEvent('tracking_off');
    log('Suivi désactivé');
  }}
  await loadEvents();
}}

function drawLoop() {{
  if (!stream) return;
  ctx.clearRect(0, 0, overlay.width, overlay.height);
  if (trackingEnabled) detectMotion();
  animationId = requestAnimationFrame(drawLoop);
}}

async function detectMotion() {{
  const w = overlay.width, h = overlay.height;
  if (!w || !h) return;
  const temp = document.createElement('canvas');
  temp.width = w; temp.height = h;
  const tctx = temp.getContext('2d', {{ willReadFrequently: true }});
  tctx.drawImage(video, 0, 0, w, h);
  const frame = tctx.getImageData(0, 0, w, h).data;
  if (prevFrame) {{
    let diff = 0;
    for (let i=0; i<frame.length; i+=64) diff += Math.abs(frame[i]-prevFrame[i]);
    if (diff > 150000) {{
      motionCount += 1; motionCountEl.textContent = motionCount;
      ctx.strokeStyle = '#ff5d73'; ctx.lineWidth = 4;
      ctx.strokeRect(24,24,w-48,h-48);
      ctx.fillStyle = '#ff5d73'; ctx.font = 'bold 22px Arial';
      ctx.fillText('MOUVEMENT DÉTECTÉ', 28, 55);
      if (motionCount % 10 === 0) {{
        await persistEvent('motion_detected', `count=${{motionCount}}`);
        await loadEvents();
      }}
    }}
  }}
  prevFrame = frame;
}}

async function snapshot() {{
  if (!stream) {{ log("Démarre la caméra d'abord."); return; }}
  const shot = document.createElement('canvas');
  shot.width = video.videoWidth; shot.height = video.videoHeight;
  shot.getContext('2d').drawImage(video,0,0,shot.width,shot.height);
  const a = document.createElement('a');
  const filename = `capture_${{new Date().toISOString().replace(/[:.]/g, '-')}}.png`;
  a.href = shot.toDataURL('image/png'); a.download = filename; a.click();
  await persistEvent('snapshot', filename);
  await loadEvents();
  log('Capture image sauvegardée');
}}

document.getElementById('startBtn').onclick = startCamera;
document.getElementById('stopBtn').onclick = async () => {{ await stopRecording(); await stopCamera(); }};
document.getElementById('recordBtn').onclick = async () => {{
  if (mediaRecorder && mediaRecorder.state === 'recording') {{
    await stopRecording();
    document.getElementById('recordBtn').textContent = '⏺️ Démarrer enregistrement';
  }} else {{
    await startRecording();
    document.getElementById('recordBtn').textContent = '⏹️ Arrêter enregistrement';
  }}
}};
document.getElementById('trackBtn').onclick = async () => {{
  await toggleTracking();
  document.getElementById('trackBtn').textContent = trackingEnabled ? '🎯 Désactiver suivi' : '🎯 Activer suivi';
}};
document.getElementById('snapshotBtn').onclick = snapshot;
document.getElementById('refreshDbBtn').onclick = loadEvents;

navigator.mediaDevices.getUserMedia({{ video: true, audio: false }})
  .then(s => {{ s.getTracks().forEach(t => t.stop()); return listCameras(); }})
  .then(loadEvents)
  .catch(() => log('Autorise la caméra dans le navigateur pour continuer.'));
</script>
</body></html>
"""


@app.post("/api/events")
def create_event(payload: Dict[str, Any]) -> Dict[str, str]:
    event_type = str(payload.get("event_type", "unknown"))
    details = str(payload.get("details", ""))
    log_event(event_type=event_type, details=details)
    return {"status": "ok"}


@app.get("/api/events")
def list_events(limit: int = 100) -> Dict[str, List[Dict[str, Any]]]:
    safe_limit = max(1, min(limit, 500))
    with _db() as conn:
        rows = conn.execute(
            "SELECT id, event_type, details, created_at FROM events ORDER BY id DESC LIMIT ?",
            (safe_limit,),
        ).fetchall()
    return {"events": [dict(r) for r in rows]}


@app.post("/api/recordings")
def create_recording(payload: Dict[str, Any]) -> Dict[str, str]:
    with _db() as conn:
        conn.execute(
            "INSERT INTO recordings(filename, duration_seconds, size_bytes, created_at) VALUES (?, ?, ?, ?)",
            (
                str(payload.get("filename", "unknown.webm")),
                float(payload.get("duration_seconds", 0.0)),
                int(payload.get("size_bytes", 0)),
                datetime.utcnow().isoformat(),
            ),
        )
    return {"status": "ok"}


@app.get("/api/recordings")
def list_recordings(limit: int = 100) -> Dict[str, List[Dict[str, Any]]]:
    safe_limit = max(1, min(limit, 500))
    with _db() as conn:
        rows = conn.execute(
            "SELECT id, filename, duration_seconds, size_bytes, created_at FROM recordings ORDER BY id DESC LIMIT ?",
            (safe_limit,),
        ).fetchall()
    return {"recordings": [dict(r) for r in rows]}


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "app": "surveillance", "database": str(DB_PATH)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("surveillance_app:app", host="0.0.0.0", port=8500, reload=False)
