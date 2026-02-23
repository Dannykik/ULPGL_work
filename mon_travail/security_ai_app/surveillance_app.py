from datetime import datetime
from pathlib import Path
from typing import Dict

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="Smart Surveillance App", version="1.0.0")

RECORDINGS_DIR = Path("recordings")
RECORDINGS_DIR.mkdir(exist_ok=True)


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
      --bg: #0b1020;
      --panel: #151b2f;
      --accent: #6d8cff;
      --danger: #ff5d73;
      --ok: #3ddc97;
      --text: #eef3ff;
      --muted: #a3b1d1;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, Segoe UI, Arial, sans-serif;
      background: radial-gradient(circle at top right, #1b2342, var(--bg));
      color: var(--text);
      min-height: 100vh;
    }}
    .container {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 24px;
    }}
    .header {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      margin-bottom: 20px;
    }}
    h1 {{ margin: 0; font-size: 2rem; }}
    .muted {{ color: var(--muted); }}

    .layout {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 20px;
    }}
    @media (max-width: 900px) {{
      .layout {{ grid-template-columns: 1fr; }}
    }}

    .panel {{
      background: linear-gradient(145deg, #161d35, var(--panel));
      border: 1px solid #2a355f;
      border-radius: 16px;
      padding: 16px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
    }}

    .video-wrap {{
      position: relative;
      width: 100%;
      border-radius: 12px;
      overflow: hidden;
      border: 1px solid #2f3b69;
      background: #0b1020;
      aspect-ratio: 16/9;
    }}
    video, canvas {{
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      object-fit: cover;
    }}

    .badge {{
      display: inline-block;
      padding: 6px 10px;
      border-radius: 999px;
      font-size: 0.85rem;
      font-weight: 600;
      margin-right: 6px;
      background: #263260;
      border: 1px solid #3a4c8f;
    }}
    .badge.ok {{ border-color: #2a7f61; background: #144435; }}
    .badge.danger {{ border-color: #8d2f44; background: #4d1b28; }}

    .controls {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 10px;
      margin-top: 14px;
    }}
    button, select {{
      width: 100%;
      border: 1px solid #3a4c8f;
      background: #1f2a4f;
      color: var(--text);
      border-radius: 10px;
      padding: 11px 12px;
      cursor: pointer;
      font-weight: 600;
      transition: transform .08s ease, opacity .2s ease;
    }}
    button:hover {{ opacity: .95; }}
    button:active {{ transform: translateY(1px); }}
    button.primary {{ background: linear-gradient(90deg, #4464ff, var(--accent)); }}
    button.stop {{ background: linear-gradient(90deg, #ff5370, var(--danger)); border-color: #a33a4f; }}
    button.secondary {{ background: #24325f; }}

    .stats {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-top: 12px;
    }}
    .card {{
      background: #0f162d;
      border: 1px solid #293764;
      border-radius: 10px;
      padding: 10px;
    }}
    .card h3 {{ margin: 0 0 4px; font-size: .9rem; color: var(--muted); font-weight: 500; }}
    .card p {{ margin: 0; font-size: 1.2rem; font-weight: 700; }}

    .log {{
      margin-top: 12px;
      max-height: 250px;
      overflow: auto;
      background: #0d1428;
      border: 1px solid #27345d;
      border-radius: 10px;
      padding: 10px;
      font-size: .9rem;
    }}
    .log-line {{ margin: 0 0 6px; color: #d6e0ff; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div>
        <h1>🛡️ Application de Surveillance</h1>
        <p class="muted">Caméra locale (PC / téléphone), enregistrement et suivi de mouvement.</p>
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
          <button id="recordBtn" class="secondary">⏺️ Démarrer enregistrement</button>
          <button id="trackBtn" class="secondary">🎯 Activer suivi</button>
          <button id="snapshotBtn" class="secondary">📸 Capture image</button>
        </div>
      </div>

      <div class="panel">
        <h2 style="margin-top:0">État & journal</h2>
        <div class="stats">
          <div class="card"><h3>Mode</h3><p id="modeLabel">Inactif</p></div>
          <div class="card"><h3>Enregistrement</h3><p id="recordingLabel">Non</p></div>
          <div class="card"><h3>Mouvements détectés</h3><p id="motionCount">0</p></div>
          <div class="card"><h3>Caméra</h3><p id="cameraName">-</p></div>
        </div>

        <div class="log" id="log"></div>
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
const logEl = document.getElementById('log');

let stream = null;
let mediaRecorder = null;
let recordedChunks = [];
let trackingEnabled = false;
let motionCount = 0;
let animationId = null;
let prevFrame = null;

function log(message) {{
  const p = document.createElement('p');
  p.className = 'log-line';
  p.textContent = `[${{new Date().toLocaleTimeString()}}] ${{message}}`;
  logEl.prepend(p);
}}

function setBadge(el, text, state = 'default') {{
  el.textContent = text;
  el.className = `badge ${{state}}`;
}}

async function listCameras() {{
  const devices = await navigator.mediaDevices.enumerateDevices();
  const cams = devices.filter(d => d.kind === 'videoinput');
  cameraSelect.innerHTML = '';
  cams.forEach((cam, idx) => {{
    const option = document.createElement('option');
    option.value = cam.deviceId;
    option.textContent = cam.label || `Caméra ${{idx + 1}}`;
    cameraSelect.appendChild(option);
  }});
}}

async function startCamera() {{
  try {{
    if (stream) stopCamera();

    const selected = cameraSelect.value;
    const constraints = selected
      ? {{ video: {{ deviceId: {{ exact: selected }} }}, audio: false }}
      : {{ video: {{ facingMode: 'environment' }}, audio: false }};

    stream = await navigator.mediaDevices.getUserMedia(constraints);
    video.srcObject = stream;

    const track = stream.getVideoTracks()[0];
    const settings = track.getSettings();
    cameraNameEl.textContent = track.label || 'Caméra active';
    modeLabel.textContent = 'Surveillance';
    setBadge(cameraStatus, 'Caméra active', 'ok');
    log(`Caméra démarrée (${{settings.width || '?'}}x${{settings.height || '?'}})`);

    await new Promise(r => video.onloadedmetadata = r);
    overlay.width = video.videoWidth;
    overlay.height = video.videoHeight;
    drawLoop();
  }} catch (err) {{
    log('Erreur caméra: ' + err.message);
    setBadge(cameraStatus, 'Erreur caméra', 'danger');
  }}
}}

function stopCamera() {{
  if (animationId) cancelAnimationFrame(animationId);
  animationId = null;
  if (stream) {{
    stream.getTracks().forEach(t => t.stop());
    stream = null;
  }}
  video.srcObject = null;
  prevFrame = null;
  ctx.clearRect(0, 0, overlay.width, overlay.height);
  modeLabel.textContent = 'Inactif';
  cameraNameEl.textContent = '-';
  setBadge(cameraStatus, 'Caméra arrêtée');
  log('Caméra arrêtée');
}}

function startRecording() {{
  if (!stream) {{ log('Démarre la caméra d\'abord.'); return; }}
  recordedChunks = [];
  mediaRecorder = new MediaRecorder(stream, {{ mimeType: 'video/webm' }});
  mediaRecorder.ondataavailable = e => {{ if (e.data.size > 0) recordedChunks.push(e.data); }};
  mediaRecorder.onstop = () => {{
    const blob = new Blob(recordedChunks, {{ type: 'video/webm' }});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `surveillance_${{new Date().toISOString().replace(/[:.]/g, '-')}}.webm`;
    a.click();
    URL.revokeObjectURL(url);
    log('Enregistrement sauvegardé.');
  }};
  mediaRecorder.start();
  recordingLabel.textContent = 'Oui';
  log('Enregistrement démarré.');
}}

function stopRecording() {{
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {{
    mediaRecorder.stop();
    recordingLabel.textContent = 'Non';
    log('Enregistrement arrêté.');
  }}
}}

function toggleTracking() {{
  trackingEnabled = !trackingEnabled;
  if (!trackingEnabled) {{
    prevFrame = null;
    setBadge(trackingStatus, 'Suivi OFF');
    log('Suivi désactivé.');
  }} else {{
    setBadge(trackingStatus, 'Suivi ON', 'ok');
    log('Suivi activé (détection de mouvement).');
  }}
}}

function drawLoop() {{
  if (!stream) return;
  ctx.clearRect(0, 0, overlay.width, overlay.height);

  if (trackingEnabled) detectMotion();

  animationId = requestAnimationFrame(drawLoop);
}}

function detectMotion() {{
  const w = overlay.width;
  const h = overlay.height;
  if (!w || !h) return;

  const temp = document.createElement('canvas');
  temp.width = w;
  temp.height = h;
  const tctx = temp.getContext('2d', {{ willReadFrequently: true }});
  tctx.drawImage(video, 0, 0, w, h);
  const frame = tctx.getImageData(0, 0, w, h).data;

  if (prevFrame) {{
    let diff = 0;
    const step = 4 * 16;
    for (let i = 0; i < frame.length; i += step) {{
      diff += Math.abs(frame[i] - prevFrame[i]);
    }}

    if (diff > 150000) {{
      motionCount++;
      motionCountEl.textContent = motionCount;
      ctx.strokeStyle = '#ff5d73';
      ctx.lineWidth = 4;
      ctx.strokeRect(20, 20, w - 40, h - 40);
      ctx.font = 'bold 22px Arial';
      ctx.fillStyle = '#ff5d73';
      ctx.fillText('MOUVEMENT DÉTECTÉ', 24, 52);
    }}
  }}

  prevFrame = frame;
}}

function snapshot() {{
  if (!stream) {{ log('Démarre la caméra d\'abord.'); return; }}
  const shot = document.createElement('canvas');
  shot.width = video.videoWidth;
  shot.height = video.videoHeight;
  const sctx = shot.getContext('2d');
  sctx.drawImage(video, 0, 0, shot.width, shot.height);
  const a = document.createElement('a');
  a.href = shot.toDataURL('image/png');
  a.download = `capture_${{new Date().toISOString().replace(/[:.]/g, '-')}}.png`;
  a.click();
  log('Capture image sauvegardée.');
}}

document.getElementById('startBtn').onclick = startCamera;
document.getElementById('stopBtn').onclick = () => {{ stopRecording(); stopCamera(); }};
document.getElementById('recordBtn').onclick = () => {{
  if (mediaRecorder && mediaRecorder.state === 'recording') {{
    stopRecording();
    document.getElementById('recordBtn').textContent = '⏺️ Démarrer enregistrement';
  }} else {{
    startRecording();
    document.getElementById('recordBtn').textContent = '⏹️ Arrêter enregistrement';
  }}
}};
document.getElementById('trackBtn').onclick = () => {{
  toggleTracking();
  document.getElementById('trackBtn').textContent = trackingEnabled ? '🎯 Désactiver suivi' : '🎯 Activer suivi';
}};
document.getElementById('snapshotBtn').onclick = snapshot;

navigator.mediaDevices.getUserMedia({{ video: true, audio: false }})
  .then(s => {{ s.getTracks().forEach(t => t.stop()); return listCameras(); }})
  .catch(() => log('Autorise la caméra dans ton navigateur pour continuer.'));
</script>
</body>
</html>
"""


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "app": "surveillance"}
