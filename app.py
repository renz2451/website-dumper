from flask import Flask, render_template, request, jsonify
import os, subprocess, threading, time, shutil

app = Flask(__name__)
DOWNLOADS_DIR = "downloads"
LOG_FILE = "logs/latest.log"
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
os.makedirs("logs", exist_ok=True)

def run_wget(command):
    with open(LOG_FILE, "w") as logfile:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            logfile.write(line)
            logfile.flush()
        process.wait()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dump', methods=['POST'])
def dump_site():
    data = request.json
    url = data['url']
    depth = data.get('depth', '0')
    rate = data.get('rate', 'unlimited')
    wait = data.get('wait', '1')

    if not url.startswith(('http://', 'https://')):
        return jsonify({'status': 'error', 'message': 'Invalid URL'})

    domain = url.replace('http://', '').replace('https://', '').split('/')[0]
    save_path = os.path.join(DOWNLOADS_DIR, domain)

    cmd = [
        "wget", "--mirror", "--convert-links", "--adjust-extension",
        "--page-requisites", "--no-parent", "--verbose",
        f"--wait={wait}", f"--directory-prefix={save_path}"
    ]
    if depth != "0":
        cmd += ["-l", depth]
    if rate != "unlimited":
        cmd += ["--limit-rate", rate]
    cmd.append(url)

    threading.Thread(target=run_wget, args=(cmd,), daemon=True).start()
    return jsonify({"status": "started", "default": domain})

@app.route('/logs')
def read_logs():
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            for line in f.readlines()[-30:]:
                l = line.lower()
                if ".html" in l:
                    tag = "📄 HTML"
                elif ".css" in l:
                    tag = "🎨 CSS"
                elif ".js" in l:
                    tag = "📜 JS"
                elif any(x in l for x in [".jpg", ".png", ".webp", ".gif"]):
                    tag = "🖼️ Image"
                elif ".mp4" in l:
                    tag = "🎥 Video"
                elif ".mp3" in l or ".wav" in l:
                    tag = "🎵 Audio"
                elif "saving to:" in l:
                    tag = "📥 Saving"
                elif "error" in l:
                    tag = "❌ Error"
                else:
                    tag = "🔄"
                logs.append(f"{tag}: {line.strip()}")
    return jsonify({"logs": logs})

@app.route('/rename_and_move', methods=['POST'])
def rename_and_move():
    data = request.json
    old = data['old']
    new = data['new']
    src = os.path.join(DOWNLOADS_DIR, old)
    dst = f"/sdcard/Download/{new}"

    try:
        shutil.move(src, dst)
        return jsonify({
            "status": "success",
            "url": f"file://{dst}/{new}/index.html"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5050)
