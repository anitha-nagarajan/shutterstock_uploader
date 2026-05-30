import csv
import json
import os
import sys
import webbrowser
from pathlib import Path
from threading import Timer

from flask import Flask, jsonify, render_template_string, request, send_file

app = Flask(__name__)
FOLDER_PATH = None
METADATA_FILE = None

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Shutterstock Upload Review</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0f0f0f;
    --surface: #1a1a1a;
    --surface2: #222;
    --border: #2e2e2e;
    --accent: #e8ff47;
    --accent-dim: rgba(232,255,71,0.12);
    --text: #f0f0f0;
    --muted: #888;
    --danger: #ff5c5c;
    --success: #47ff9a;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: 'DM Sans', sans-serif; min-height: 100vh; }

  header {
    padding: 28px 40px;
    border-bottom: 1px solid var(--border);
    display: flex; align-items: center; justify-content: space-between;
    position: sticky; top: 0; background: var(--bg); z-index: 100;
  }
  .logo { font-family: 'DM Serif Display', serif; font-size: 22px; letter-spacing: -0.5px; }
  .logo span { color: var(--accent); }
  .header-actions { display: flex; gap: 12px; align-items: center; }
  .badge { background: var(--accent-dim); color: var(--accent); padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: 500; }

  .btn {
    padding: 10px 22px; border-radius: 8px; font-size: 14px; font-weight: 600;
    cursor: pointer; border: none; transition: all 0.2s; font-family: inherit;
  }
  .btn-primary { background: var(--accent); color: #0f0f0f; }
  .btn-primary:hover { background: #d4eb2a; transform: translateY(-1px); }
  .btn-primary:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }
  .btn-outline { background: transparent; color: var(--text); border: 1px solid var(--border); }
  .btn-outline:hover { border-color: var(--accent); color: var(--accent); }

  .progress-bar {
    height: 3px; background: var(--border);
    position: sticky; top: 81px; z-index: 99;
  }
  .progress-fill { height: 100%; background: var(--accent); transition: width 0.4s ease; }

  main { max-width: 1400px; margin: 0 auto; padding: 40px; }

  .summary {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 40px;
  }
  .stat-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 12px; padding: 20px 24px;
  }
  .stat-label { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }
  .stat-value { font-family: 'DM Serif Display', serif; font-size: 32px; }
  .stat-value.green { color: var(--success); }
  .stat-value.yellow { color: var(--accent); }

  .photo-grid { display: flex; flex-direction: column; gap: 24px; }

  .photo-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 16px; overflow: hidden;
    display: grid; grid-template-columns: 280px 1fr;
    transition: border-color 0.2s;
  }
  .photo-card.approved { border-color: var(--success); }
  .photo-card.approved .card-status { background: rgba(71,255,154,0.08); }

  .photo-preview {
    position: relative; background: #111;
    display: flex; align-items: center; justify-content: center;
    overflow: hidden;
  }
  .photo-preview img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .photo-name {
    position: absolute; bottom: 0; left: 0; right: 0;
    background: linear-gradient(transparent, rgba(0,0,0,0.8));
    padding: 20px 12px 10px;
    font-size: 11px; color: #ccc; word-break: break-all;
  }

  .card-body { padding: 28px; display: flex; flex-direction: column; gap: 20px; }

  .card-status {
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 14px; border-radius: 8px; background: var(--surface2);
  }
  .status-dot {
    width: 8px; height: 8px; border-radius: 50%; margin-right: 8px;
    background: var(--muted); display: inline-block;
  }
  .approved .status-dot { background: var(--success); }
  .status-text { font-size: 13px; color: var(--muted); display: flex; align-items: center; }
  .approved .status-text { color: var(--success); }

  .field-group { display: flex; flex-direction: column; gap: 6px; }
  .field-label { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }

  input[type="text"], textarea, select {
    background: var(--surface2); border: 1px solid var(--border);
    color: var(--text); border-radius: 8px; padding: 10px 14px;
    font-family: 'DM Sans', sans-serif; font-size: 14px;
    width: 100%; transition: border-color 0.2s; resize: vertical;
  }
  input:focus, textarea:focus, select:focus {
    outline: none; border-color: var(--accent);
  }
  textarea { min-height: 70px; }

  .keywords-wrap {
    background: var(--surface2); border: 1px solid var(--border);
    border-radius: 8px; padding: 10px 14px; min-height: 70px;
    display: flex; flex-wrap: wrap; gap: 6px; cursor: text;
    transition: border-color 0.2s;
  }
  .keywords-wrap:focus-within { border-color: var(--accent); }
  .keyword-tag {
    background: var(--accent-dim); color: var(--accent);
    border-radius: 4px; padding: 3px 8px; font-size: 12px;
    display: flex; align-items: center; gap: 4px;
  }
  .keyword-tag button {
    background: none; border: none; color: var(--accent);
    cursor: pointer; font-size: 14px; line-height: 1; padding: 0;
  }
  .keyword-input {
    background: none; border: none; color: var(--text);
    font-family: 'DM Sans', sans-serif; font-size: 13px;
    outline: none; flex: 1; min-width: 120px; padding: 2px 4px;
  }
  .kw-count { font-size: 11px; color: var(--muted); margin-top: 4px; }

  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

  .card-actions { display: flex; gap: 10px; margin-top: 4px; }
  .btn-approve {
    padding: 10px 24px; border-radius: 8px; font-size: 14px; font-weight: 600;
    cursor: pointer; border: 1px solid var(--success); background: transparent;
    color: var(--success); font-family: inherit; transition: all 0.2s;
  }
  .btn-approve:hover, .approved .btn-approve {
    background: var(--success); color: #0f0f0f;
  }
  .btn-reset {
    padding: 10px 18px; border-radius: 8px; font-size: 14px;
    cursor: pointer; border: 1px solid var(--border); background: transparent;
    color: var(--muted); font-family: inherit; transition: all 0.2s;
  }
  .btn-reset:hover { border-color: var(--danger); color: var(--danger); }

  .export-section {
    margin-top: 48px; padding: 32px; background: var(--surface);
    border: 1px solid var(--border); border-radius: 16px;
    display: flex; align-items: center; justify-content: space-between;
    gap: 24px;
  }
  .export-info h3 { font-family: 'DM Serif Display', serif; font-size: 22px; margin-bottom: 6px; }
  .export-info p { color: var(--muted); font-size: 14px; line-height: 1.6; }

  .toast {
    position: fixed; bottom: 32px; right: 32px;
    background: var(--surface); border: 1px solid var(--accent);
    color: var(--accent); padding: 14px 20px; border-radius: 10px;
    font-size: 14px; font-weight: 500;
    transform: translateY(80px); opacity: 0;
    transition: all 0.3s ease; z-index: 999;
  }
  .toast.show { transform: translateY(0); opacity: 1; }

  @media (max-width: 900px) {
    .photo-card { grid-template-columns: 1fr; }
    .photo-preview { height: 200px; }
    main { padding: 20px; }
    .two-col { grid-template-columns: 1fr; }
    .summary { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>
<header>
  <div class="logo">shutter<span>prep</span></div>
  <div class="header-actions">
    <span class="badge" id="approvedBadge">0 approved</span>
    <button class="btn btn-outline" onclick="approveAll()">Approve All</button>
    <button class="btn btn-primary" id="exportBtn" onclick="exportCSV()" disabled>Export CSV</button>
  </div>
</header>
<div class="progress-bar"><div class="progress-fill" id="progressFill" style="width:0%"></div></div>

<main>
  <div class="summary">
    <div class="stat-card">
      <div class="stat-label">Total Photos</div>
      <div class="stat-value" id="totalCount">0</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Approved</div>
      <div class="stat-value green" id="approvedCount">0</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Pending Review</div>
      <div class="stat-value yellow" id="pendingCount">0</div>
    </div>
  </div>

  <div class="photo-grid" id="photoGrid"></div>

  <div class="export-section">
    <div class="export-info">
      <h3>Ready to upload?</h3>
      <p>Export a Shutterstock-formatted CSV, then drag your photos + CSV into<br>the Shutterstock bulk upload portal.</p>
    </div>
    <button class="btn btn-primary" id="exportBtn2" onclick="exportCSV()" disabled>Export CSV & Open Shutterstock</button>
  </div>
</main>

<div class="toast" id="toast"></div>

<script>
let photos = [];

async function loadPhotos() {
  const res = await fetch('/api/photos');
  photos = await res.json();
  renderAll();
}

function renderAll() {
  const grid = document.getElementById('photoGrid');
  grid.innerHTML = '';
  photos.forEach((p, i) => grid.appendChild(renderCard(p, i)));
  updateStats();
}

function renderCard(p, i) {
  const card = document.createElement('div');
  card.className = 'photo-card' + (p.approved ? ' approved' : '');
  card.id = `card-${i}`;

  const kwHtml = (p.keywords || []).map((kw, ki) =>
    `<span class="keyword-tag">${kw}<button onclick="removeKeyword(${i},${ki})">×</button></span>`
  ).join('');

  card.innerHTML = `
    <div class="photo-preview">
      <img src="/photo/${i}" alt="${p.filename}" loading="lazy">
      <div class="photo-name">${p.filename}</div>
    </div>
    <div class="card-body">
      <div class="card-status">
        <span class="status-text"><span class="status-dot"></span>${p.approved ? 'Approved' : 'Pending review'}</span>
        <span style="font-size:12px;color:var(--muted)">${p.filename}</span>
      </div>

      <div class="field-group">
        <label class="field-label">Title</label>
        <input type="text" value="${esc(p.title)}" oninput="update(${i},'title',this.value)" maxlength="200">
      </div>

      <div class="field-group">
        <label class="field-label">Description</label>
        <textarea oninput="update(${i},'description',this.value)">${esc(p.description)}</textarea>
      </div>

      <div class="two-col">
        <div class="field-group">
          <label class="field-label">Category</label>
          <select onchange="update(${i},'category',this.value)">${categoryOptions(p.category)}</select>
        </div>
        <div class="field-group">
          <label class="field-label">License Type</label>
          <select onchange="update(${i},'license_type',this.value)">
            <option value="commercial" ${p.license_type==='commercial'?'selected':''}>Commercial</option>
            <option value="editorial" ${p.license_type==='editorial'?'selected':''}>Editorial</option>
          </select>
        </div>
      </div>

      <div class="field-group">
        <label class="field-label">Keywords <span style="color:var(--accent)">(${(p.keywords||[]).length})</span></label>
        <div class="keywords-wrap" onclick="focusKwInput(${i})">
          ${kwHtml}
          <input class="keyword-input" id="kw-input-${i}" placeholder="Add keyword…"
            onkeydown="handleKwKey(event,${i})">
        </div>
        <div class="kw-count">Press Enter or comma to add · Click × to remove</div>
      </div>

      <div class="card-actions">
        <button class="btn-approve" onclick="toggleApprove(${i})">${p.approved ? '✓ Approved' : 'Approve'}</button>
        <button class="btn-reset" onclick="resetCard(${i})">Reset</button>
      </div>
    </div>`;
  return card;
}

const CATEGORIES = ["Abstract","Animals/Wildlife","Arts","Backgrounds/Textures","Beauty/Fashion","Buildings/Landmarks","Business/Finance","Celebrities","Editorial","Education","Food and drink","Healthcare/Medical","Holidays","Industrial","Interiors","Miscellaneous","Nature","Objects","Parks/Outdoor","People","Religion","Science","Signs/Symbols","Sports/Recreation","Technology","Transportation","Vintage"];

function categoryOptions(selected) {
  return CATEGORIES.map(c => `<option value="${c}" ${c===selected?'selected':''}>${c}</option>`).join('');
}

function esc(s) { return (s||'').replace(/"/g,'&quot;').replace(/</g,'&lt;'); }

function update(i, field, value) {
  photos[i][field] = value;
  save();
}

function focusKwInput(i) { document.getElementById(`kw-input-${i}`).focus(); }

function handleKwKey(e, i) {
  if (e.key === 'Enter' || e.key === ',') {
    e.preventDefault();
    const val = e.target.value.trim().replace(/,$/, '');
    if (val && !photos[i].keywords.includes(val)) {
      photos[i].keywords.push(val);
      e.target.value = '';
      refreshCard(i);
      save();
    }
  }
}

function removeKeyword(i, ki) {
  photos[i].keywords.splice(ki, 1);
  refreshCard(i);
  save();
}

function refreshCard(i) {
  const old = document.getElementById(`card-${i}`);
  const fresh = renderCard(photos[i], i);
  old.replaceWith(fresh);
  // re-focus keyword input
  setTimeout(() => focusKwInput(i), 50);
}

function toggleApprove(i) {
  photos[i].approved = !photos[i].approved;
  refreshCard(i);
  updateStats();
  save();
}

function approveAll() {
  photos.forEach(p => p.approved = true);
  renderAll();
  save();
  showToast('All photos approved!');
}

function resetCard(i) {
  if (!confirm('Reset metadata for this photo?')) return;
  fetch(`/api/reset/${i}`).then(r => r.json()).then(orig => {
    photos[i] = orig;
    refreshCard(i);
    updateStats();
    save();
  });
}

function updateStats() {
  const total = photos.length;
  const approved = photos.filter(p => p.approved).length;
  document.getElementById('totalCount').textContent = total;
  document.getElementById('approvedCount').textContent = approved;
  document.getElementById('pendingCount').textContent = total - approved;
  document.getElementById('approvedBadge').textContent = `${approved} approved`;
  document.getElementById('progressFill').style.width = total ? `${(approved/total)*100}%` : '0%';
  const canExport = approved > 0;
  document.getElementById('exportBtn').disabled = !canExport;
  document.getElementById('exportBtn2').disabled = !canExport;
}

async function save() {
  await fetch('/api/save', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(photos)
  });
  updateStats();
}

async function exportCSV() {
  showToast('Generating CSV...');
  const res = await fetch('/api/export', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(photos)
  });
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'shutterstock_upload.csv';
  a.click();
  showToast('CSV exported! Opening Shutterstock...');
  setTimeout(() => window.open('https://submit.shutterstock.com/catalog', '_blank'), 1500);
}

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3000);
}

loadPhotos();
</script>
</body>
</html>
"""


def load_metadata(folder: Path):
    meta_file = folder / "_metadata_draft.json"
    if not meta_file.exists():
        return []
    with open(meta_file) as f:
        return json.load(f)


def save_metadata(folder: Path, data: list):
    meta_file = folder / "_metadata_draft.json"
    with open(meta_file, "w") as f:
        json.dump(data, f, indent=2)


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/photos")
def get_photos():
    photos = load_metadata(Path(FOLDER_PATH))
    return jsonify(photos)


@app.route("/photo/<int:idx>")
def get_photo(idx):
    photos = load_metadata(Path(FOLDER_PATH))
    if idx >= len(photos):
        return "Not found", 404
    filepath = photos[idx]["filepath"]
    return send_file(filepath)


@app.route("/api/save", methods=["POST"])
def save_photos():
    data = request.get_json()
    save_metadata(Path(FOLDER_PATH), data)
    return jsonify({"ok": True})


@app.route("/api/reset/<int:idx>")
def reset_photo(idx):
    photos = load_metadata(Path(FOLDER_PATH))
    if idx >= len(photos):
        return jsonify({}), 404
    return jsonify(photos[idx])


@app.route("/api/export", methods=["POST"])
def export_csv():
    data = request.get_json()
    approved = [p for p in data if p.get("approved")]

    folder = Path(FOLDER_PATH)
    csv_path = folder / "shutterstock_upload.csv"

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Shutterstock bulk upload CSV headers
        writer.writerow([
            "Filename", "Description", "Keywords", "Categories", "Editorial",
            "Mature content", "Illustration"
        ])
        for p in approved:
            keywords_str = ", ".join(p.get("keywords", []))
            is_editorial = "yes" if p.get("license_type") == "editorial" else "no"
            writer.writerow([
                p["filename"],
                p.get("description", ""),
                keywords_str,
                p.get("category", ""),
                is_editorial,
                "no",
                "no",
            ])

    return send_file(
        csv_path,
        mimetype="text/csv",
        as_attachment=True,
        download_name="shutterstock_upload.csv",
    )


def open_browser():
    webbrowser.open("http://127.0.0.1:5000")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Review and approve photo metadata")
    parser.add_argument("folder", help="Path to folder containing photos and metadata")
    args = parser.parse_args()

    FOLDER_PATH = args.folder
    folder = Path(FOLDER_PATH)

    if not (folder / "_metadata_draft.json").exists():
        print(f"Error: No metadata found in '{FOLDER_PATH}'.")
        print("Please run generate_metadata.py first.")
        sys.exit(1)

    print(f"\n✅ Opening review UI at http://127.0.0.1:5000")
    print("Press Ctrl+C to stop the server.\n")

    Timer(1.2, open_browser).start()
    app.run(debug=False, port=5000)
