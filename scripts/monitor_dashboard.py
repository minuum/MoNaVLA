#!/usr/bin/env python3
"""
V5 Training & Inference Monitor Dashboard
Usage: python3 scripts/monitor_dashboard.py [--port 8080]
"""
import json
import re
import os
import sys
import subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import urllib.request

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRAIN_LOG = Path("/tmp/v5_train_log.txt")
INFER_LOG = Path("/tmp/v5_infer_log.txt")
CKPT_DIR = PROJECT_ROOT / "runs/v5_nav/kosmos/mobile_vla_v5_exp01/2026-04-10/v5-exp01-discrete"
INFER_URL = "http://localhost:8000"


def parse_training_log():
    """Parse training log for epoch-level metrics."""
    if not TRAIN_LOG.exists():
        return {"status": "no_log", "epochs": [], "checkpoints": []}

    text = TRAIN_LOG.read_text(errors="ignore")

    # Extract per-step losses for step chart (sample every 5 steps)
    step_losses = []
    for m in re.finditer(r"train_loss_step=([0-9.]+)", text):
        step_losses.append(float(m.group(1)))

    # Extract epoch-end metrics: unique (val_loss, train_loss_epoch) per epoch transition
    epoch_metrics = []
    seen = set()
    for m in re.finditer(r"Epoch (\d+):.*?val_loss=([0-9.]+), train_loss_epoch=([0-9.]+)", text):
        ep, vl, tl = int(m.group(1)), float(m.group(2)), float(m.group(3))
        key = (ep, vl, tl)
        if key not in seen:
            seen.add(key)
            epoch_metrics.append({"epoch": ep, "val_loss": vl, "train_loss": tl})

    # Deduplicate: keep only last entry per epoch
    by_epoch = {}
    for e in epoch_metrics:
        by_epoch[e["epoch"]] = e
    epochs = sorted(by_epoch.values(), key=lambda x: x["epoch"])

    # Best epoch
    best = min(epochs, key=lambda x: x["val_loss"]) if epochs else None

    # EarlyStopping
    stopped = "Signaling Trainer to stop" in text
    status = "completed" if stopped else ("running" if text.strip() else "no_log")

    # Sampled step losses (max 200 points)
    n = len(step_losses)
    if n > 200:
        step = n // 200
        step_losses = step_losses[::step]

    # Checkpoints
    checkpoints = []
    if CKPT_DIR.exists():
        for ck in sorted(CKPT_DIR.glob("epoch_*.ckpt")):
            m = re.search(r"epoch=(\d+)-val_loss=([0-9.]+)", ck.name)
            if m:
                checkpoints.append({"name": ck.name, "epoch": int(m.group(1)), "val_loss": float(m.group(2))})

    return {
        "status": status,
        "epochs": epochs,
        "best": best,
        "step_losses": step_losses,
        "checkpoints": checkpoints,
        "log_lines": text.count("\n"),
    }


def get_inference_status():
    """Check inference server health."""
    try:
        req = urllib.request.Request(f"{INFER_URL}/health", headers={"User-Agent": "monitor"})
        with urllib.request.urlopen(req, timeout=2) as r:
            data = json.loads(r.read())
        return {"online": True, "data": data}
    except Exception as e:
        return {"online": False, "error": str(e)}


def get_gpu_status():
    """Get GPU utilization via nvidia-smi."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
             "--format=csv,noheader,nounits"],
            timeout=3, text=True
        ).strip()
        parts = [p.strip() for p in out.split(",")]
        return {
            "name": parts[0],
            "util": int(parts[1]),
            "mem_used": int(parts[2]),
            "mem_total": int(parts[3]),
            "temp": int(parts[4]),
        }
    except Exception as e:
        return {"error": str(e)}


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MoNaVLA V5 Monitor</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', sans-serif; background: #0f1117; color: #e2e8f0; min-height: 100vh; }
  h1 { text-align: center; padding: 20px; font-size: 1.4rem; color: #7ee8a2; letter-spacing: 1px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; padding: 0 20px 20px; }
  .card { background: #1a1d27; border-radius: 12px; padding: 18px; border: 1px solid #2d3148; }
  .card h2 { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; color: #7c82a8; margin-bottom: 12px; }
  .badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 0.78rem; font-weight: 600; }
  .badge.completed { background: #14532d; color: #4ade80; }
  .badge.running { background: #1e3a5f; color: #60a5fa; }
  .badge.online { background: #14532d; color: #4ade80; }
  .badge.offline { background: #450a0a; color: #f87171; }
  .metric { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid #2d3148; font-size: 0.9rem; }
  .metric:last-child { border-bottom: none; }
  .metric .val { font-weight: 600; color: #f1f5f9; }
  .metric .best { color: #fbbf24; }
  .chart-wrap { position: relative; height: 220px; }
  .ckpt { font-size: 0.78rem; padding: 5px 8px; background: #12151f; border-radius: 6px; margin-top: 6px; color: #94a3b8; display: flex; justify-content: space-between; }
  .ckpt.best-ckpt { border-left: 3px solid #fbbf24; color: #fde68a; }
  .gpu-bar { background: #12151f; border-radius: 8px; height: 10px; margin-top: 4px; overflow: hidden; }
  .gpu-bar-fill { height: 100%; border-radius: 8px; transition: width 0.5s; }
  .refresh-info { text-align: center; font-size: 0.75rem; color: #4b5563; padding: 8px; }
  canvas { max-height: 220px; }
</style>
</head>
<body>
<h1>🤖 MoNaVLA V5 Training Monitor</h1>
<div id="app" class="grid"></div>
<div class="refresh-info" id="refresh-info">로딩 중...</div>

<script>
let charts = {};

async function fetchData() {
  const r = await fetch('/api/status');
  return r.json();
}

function statusBadge(status) {
  if (status === 'completed') return '<span class="badge completed">✅ Completed</span>';
  if (status === 'running') return '<span class="badge running">🔄 Running</span>';
  return '<span class="badge offline">⬜ No Log</span>';
}

function renderTraining(train) {
  const best = train.best;
  const epochs = train.epochs;

  let ckptHtml = (train.checkpoints || []).map(c => {
    const isBest = best && c.epoch === best.epoch;
    return `<div class="ckpt ${isBest ? 'best-ckpt' : ''}">
      <span>epoch ${c.epoch}</span>
      <span>val_loss ${c.val_loss.toFixed(3)} ${isBest ? '⭐' : ''}</span>
    </div>`;
  }).join('');

  return `
    <div class="card">
      <h2>Training Status</h2>
      ${statusBadge(train.status)}
      <div style="margin-top:10px">
        <div class="metric"><span>Total Epochs</span><span class="val">${epochs.length}</span></div>
        <div class="metric"><span>Best val_loss</span><span class="val best">${best ? best.val_loss.toFixed(4) : '-'} (ep ${best ? best.epoch : '-'})</span></div>
        <div class="metric"><span>Best train_loss</span><span class="val">${best ? best.train_loss.toFixed(4) : '-'}</span></div>
        <div class="metric"><span>Log Lines</span><span class="val">${train.log_lines}</span></div>
      </div>
    </div>
    <div class="card" style="grid-column: span 2">
      <h2>Loss Curve (per epoch)</h2>
      <div class="chart-wrap"><canvas id="epochChart"></canvas></div>
    </div>
    <div class="card">
      <h2>Checkpoints</h2>
      ${ckptHtml || '<div style="color:#4b5563;font-size:0.85rem">No checkpoints yet</div>'}
    </div>
    <div class="card" style="grid-column: span 2">
      <h2>Step Loss (sampled)</h2>
      <div class="chart-wrap"><canvas id="stepChart"></canvas></div>
    </div>
  `;
}

function renderInference(infer) {
  const badge = infer.online
    ? '<span class="badge online">🟢 Online</span>'
    : '<span class="badge offline">🔴 Offline</span>';
  const details = infer.online && infer.data
    ? Object.entries(infer.data).map(([k,v]) =>
        `<div class="metric"><span>${k}</span><span class="val">${JSON.stringify(v)}</span></div>`).join('')
    : `<div class="metric"><span>Error</span><span class="val" style="color:#f87171">${infer.error||''}</span></div>`;
  return `
    <div class="card">
      <h2>Inference Server :8000</h2>
      ${badge}
      <div style="margin-top:10px">${details}</div>
    </div>
  `;
}

function renderGpu(gpu) {
  if (gpu.error) return `<div class="card"><h2>GPU</h2><span style="color:#f87171">${gpu.error}</span></div>`;
  const utilColor = gpu.util > 80 ? '#4ade80' : gpu.util > 40 ? '#fbbf24' : '#60a5fa';
  const memColor = gpu.mem_used / gpu.mem_total > 0.8 ? '#f87171' : '#60a5fa';
  return `
    <div class="card">
      <h2>GPU — ${gpu.name}</h2>
      <div class="metric"><span>Utilization</span><span class="val" style="color:${utilColor}">${gpu.util}%</span></div>
      <div class="gpu-bar"><div class="gpu-bar-fill" style="width:${gpu.util}%;background:${utilColor}"></div></div>
      <div class="metric" style="margin-top:8px"><span>Memory</span><span class="val" style="color:${memColor}">${gpu.mem_used} / ${gpu.mem_total} MiB</span></div>
      <div class="gpu-bar"><div class="gpu-bar-fill" style="width:${(gpu.mem_used/gpu.mem_total*100).toFixed(1)}%;background:${memColor}"></div></div>
      <div class="metric" style="margin-top:8px"><span>Temperature</span><span class="val">${gpu.temp}°C</span></div>
    </div>
  `;
}

function drawEpochChart(epochs) {
  const ctx = document.getElementById('epochChart');
  if (!ctx) return;
  if (charts.epoch) charts.epoch.destroy();
  charts.epoch = new Chart(ctx, {
    type: 'line',
    data: {
      labels: epochs.map(e => `Ep ${e.epoch}`),
      datasets: [
        { label: 'val_loss', data: epochs.map(e => e.val_loss), borderColor: '#60a5fa', backgroundColor: 'rgba(96,165,250,0.1)', tension: 0.3, pointRadius: 4 },
        { label: 'train_loss', data: epochs.map(e => e.train_loss), borderColor: '#4ade80', backgroundColor: 'rgba(74,222,128,0.1)', tension: 0.3, pointRadius: 4 },
      ]
    },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: '#94a3b8' } } }, scales: { x: { ticks: { color: '#94a3b8' }, grid: { color: '#2d3148' } }, y: { ticks: { color: '#94a3b8' }, grid: { color: '#2d3148' } } } }
  });
}

function drawStepChart(stepLosses) {
  const ctx = document.getElementById('stepChart');
  if (!ctx) return;
  if (charts.step) charts.step.destroy();
  charts.step = new Chart(ctx, {
    type: 'line',
    data: {
      labels: stepLosses.map((_, i) => i),
      datasets: [{ label: 'train_loss (step)', data: stepLosses, borderColor: '#a78bfa', backgroundColor: 'rgba(167,139,250,0.05)', tension: 0.2, pointRadius: 0, borderWidth: 1.5 }]
    },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: '#94a3b8' } } }, scales: { x: { display: false }, y: { ticks: { color: '#94a3b8' }, grid: { color: '#2d3148' } } } }
  });
}

async function update() {
  try {
    const data = await fetchData();
    const app = document.getElementById('app');
    app.innerHTML = renderTraining(data.train) + renderInference(data.infer) + renderGpu(data.gpu);
    if (data.train.epochs.length > 0) drawEpochChart(data.train.epochs);
    if (data.train.step_losses.length > 0) drawStepChart(data.train.step_losses);
    document.getElementById('refresh-info').textContent =
      '⏱ 자동 갱신: 5초 | 마지막: ' + new Date().toLocaleTimeString('ko-KR');
  } catch(e) {
    document.getElementById('refresh-info').textContent = '오류: ' + e.message;
  }
}

update();
setInterval(update, 5000);
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # silent

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/status":
            data = {
                "train": parse_training_log(),
                "infer": get_inference_status(),
                "gpu": get_gpu_status(),
            }
            body = json.dumps(data).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/" or path == "/index.html":
            body = HTML_TEMPLATE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    os.chdir(PROJECT_ROOT)
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"✅ Dashboard running at http://localhost:{port}")
    print(f"   Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
