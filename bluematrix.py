#!/usr/bin/env python3
import os, json, time, math, subprocess
from flask import Flask, render_template_string, request

# ---------------- Capsule Constants ----------------
MB_EXPANSION_UNIT = 1.0
MB_EXPONENT = 18
MB_TOTAL = MB_EXPANSION_UNIT * (10 ** MB_EXPONENT)
MB_USED_TOTAL = 0.0

PI_GAIN = math.pi ** 3.14
HASH_RATE = 1000 * 6000
AMPLIFIER_OVERLAY = 1000 * math.e * 6000
GATEWAY_RESISTANCE = 0.8
LATENCY = 1.2

# ---------------- Flask App ----------------
app = Flask(__name__)
UPLOAD_DIR = "capsule_uploads"
PROGRAM_DIR = "capsule_programs"
INDEX_PATH = "capsule_index.json"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROGRAM_DIR, exist_ok=True)

# ---------------- BIOS Emitter ----------------
def emit_capsule_bios(path="capsule_bios.json"):
    seed = "rhinestone_cowboy"
    signal = sum(ord(c) for c in seed) * math.pi * 3.14
    ip = f"capsule://{hex(int(signal))[-8:]}"
    bios = {
        "capsule_id": "RC-1975",
        "symbolic_seed": seed,
        "signal": signal,
        "ip": ip,
        "amplifier_overlay": AMPLIFIER_OVERLAY,
        "hash_rate": HASH_RATE,
        "gateway_resistance": GATEWAY_RESISTANCE,
        "latency": LATENCY,
        "remix_rights": "granted",
        "runtime_mode": "sovereign",
        "capsule_count": 0,
        "last_capsule": None,
        "boot_time": time.time()
    }
    with open(path, "w") as f:
        json.dump(bios, f, indent=2)
    print(f"🧬 BIOS emitted to {path}")
    return bios

# ---------------- Gateway Logic ----------------
def capsule_gateway_access(nb_signal):
    return nb_signal * PI_GAIN * HASH_RATE

def capsule_dns_forward(domain_name):
    return f"capsule://ip_{domain_name.replace('.', '_')}"

def capsule_dns_reverse(ip_address):
    return f"capsule://reverse_{ip_address.replace('.', '_')}"

def capsule_uplink(query):
    nb_signal = float('inf')
    gateway_flux = capsule_gateway_access(nb_signal)

    if query.replace('.', '').isdigit():
        symbolic_address = capsule_dns_reverse(query)
    elif '.' in query:
        symbolic_address = capsule_dns_forward(query)
    else:
        symbolic_address = f"capsule://{query.replace(' ', '_').lower()}"

    status = "connected" if gateway_flux >= 1e3 else "offline"
    response_text = (
        f"Symbolic uplink to '{query}' established via capsule gateway."
        if status == "connected"
        else "⚠️ Signal too weak. Try adjusting amplifier overlays."
    )

    return {
        "status": status,
        "address": symbolic_address,
        "mb_signal": nb_signal,
        "gateway_flux": gateway_flux,
        "response": response_text
    }

# ---------------- Matrix UI ----------------
@app.route("/")
def capsule_ui():
    template = """
    <!DOCTYPE html>
    <html>
    <head>
    <title>Blue Matrix Web Exabyte Engine </title>  
    <style>  
    body { background: #001122; color: #00ccff; font-family: monospace; padding: 2em; }  
    input, textarea, button { background: #000; color: #00ccff; border: 1px solid #00ccff; margin: 0.5em 0; width: 100%; }  
    h2 { color: #00ccff; border-bottom: 1px solid #00ccff; padding-bottom: 0.2em; }  
    .section { margin-bottom: 2em; }  
    #terminal-output { background: #000; color: #00ccff; padding: 1em; height: 300px; overflow-y: auto; border: 1px solid #00ccff; }  
    </style>
    </head>
    <body>  
    <h1>.Blue Matrix Web Exabyte Engine</h1>  

    <div class="section">    
      <h2>Upload / Create Capsule</h2>    
      <form method="POST" action="/capsule_create" enctype="multipart/form-data">    
        <label>File / Photo (optional):</label><input type="file" name="file">    
        <label>Title:</label><input type="text" name="title" placeholder="Capsule Title">    
        <label>Description / Program Text:</label><textarea name="description" placeholder="Description or program logic"></textarea>    
        <label>Tags (comma separated):</label><input type="text" name="tags" placeholder="tag1,tag2">    
        <label><input type="checkbox" name="installable"> Make this capsule an installable program?</label>    
        <button type="submit">Save Capsule</button>    
      </form>    
    </div>    

    <div class="section">    
      <h2>Search / Directory</h2>    
      <form method="POST" action="/capsule_search">    
        <input type="text" name="query" placeholder="Search by title, tags, description">    
        <button type="submit">Search</button>    
        <button onclick="location.href='/capsule_search';return false;">All Capsules</button>    
      </form>    
    </div>    

    <div class="section">    
      <h2>Storage Status (Symbolic)</h2>    
      <p>Capacity: 1.0EB</p>    
      <p>Used: 0.00</p>    
      <p>Free: 1.0EB</p>    
      <p>Symbolic Speed: 100000 Gbps</p>    
      <button onclick="location.href='/reset_storage';return false;">Reset Symbolic Storage</button>    
    </div>    

    <div class="section">    
      <h2>Capsule Terminal (Real Shell)</h2>    
      <div id="terminal-output"></div>    
      <form id="terminal-form">    
        <input type="text" id="terminal-input" placeholder="Type shell command, e.g. pip install flask">    
        <button type="submit">Send</button>    
      </form>    
    </div>    

    <script>    
    document.getElementById("terminal-form").addEventListener("submit", function(e) {    
      e.preventDefault();    
      const cmd = document.getElementById("terminal-input").value;    
      fetch("/terminal_exec", {    
        method: "POST",    
        headers: { "Content-Type": "application/x-www-form-urlencoded" },    
        body: "cmd=" + encodeURIComponent(cmd)    
      })    
      .then(res => res.text())    
      .then(text => {    
        const terminal = document.getElementById("terminal-output");    
        terminal.innerHTML += "<pre>" + text + "</pre>";    
        terminal.scrollTop = terminal.scrollHeight;    
        document.getElementById("terminal-input").value = "";
      });
    });
    </script>

    </body></html>
    """
    return render_template_string(template)

# ---------------- Symbolic Compression ----------------
def symbolic_compress(data):
    return str(hash(data))[:64]

# ---------------- Anatomy Overlay ----------------
def anatomy_overlay(data):
    score = sum(ord(c) for c in data) % 256
    rgb = [ord(c) % 256 for c in data[:3]]
    return {
        "eruption_score": score,
        "rgb": rgb,
        "symbolic_overlay": f"eruption:{score}-rgb:{rgb}"
    }

# ---------------- vhBTC Payout ----------------
def vhBTC_payout(capsule_text):
    flux = sum(ord(c) for c in capsule_text) * AMPLIFIER_OVERLAY
    payout = (flux / HASH_RATE) * 0.00000001
    return payout

# ---------------- Capsule Upload ----------------
@app.route("/capsule_create", methods=["POST"])
def capsule_create():
    title = request.form.get("title", "untitled")
    description = request.form.get("description", "")
    tags = request.form.get("tags", "")
    installable = request.form.get("installable") == "on"
    file = request.files.get("file")
    filename = file.filename if file else None

    capsule_dir = os.path.join(PROGRAM_DIR, title)
    os.makedirs(capsule_dir, exist_ok=True)

    if filename:
        file_path = os.path.join(capsule_dir, filename)
        file.save(file_path)

    overlay = symbolic_compress(title + description + tags)
    eruption = anatomy_overlay(title + description)
    payout = vhBTC_payout(title + description)

    entry = {
        "title": title,
        "description": description,
        "tags": tags,
        "file": filename,
        "overlay": overlay,
        "eruption": eruption,
        "payout": payout,
        "timestamp": time.time(),
        "status": "Created",
        "remix_rights": "granted"
    }

    index = []
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, "r") as f:
            index = json.load(f)
    index.append(entry)
    with open(INDEX_PATH, "w") as f:
        json.dump(index, f, indent=2)

    if installable and filename and filename.endswith(".sh"):
        result = subprocess.run(["bash", os.path.join(capsule_dir, filename)], capture_output=True, text=True)
        entry["status"] = "Installed"
        entry["install_output"] = result.stdout + result.stderr
        with open(INDEX_PATH, "w") as f:
            json.dump(index, f, indent=2)

    return render_template_string(f"""
    <!DOCTYPE html>
    <html>
    <head><title>Capsule Created</title>
    <style>
    body {{ background: #001122; color: #00ccff; font-family: monospace; padding: 2em; }}
    pre, p, h2, a {{ color: #00ccff; font-family: monospace; }}
    a {{ text-decoration: underline; }}
    </style></head>
    <body>
    <h2>Capsule Created</h2>
    <pre>{json.dumps(entry, indent=2)}</pre>
    <a href='/'>Back</a>
    </body></html>
    """)

# ---------------- Matrix Response Wrapper ----------------
def matrix_response(text):
    return render_template_string(f"""
    <!DOCTYPE html>
    <html>
    <head><title>Capsule Terminal</title>
    <style>
    body {{ background: #001122; color: #00ccff; font-family: monospace; padding: 2em; }}
    pre, p, h2, a {{ color: #00ccff; font-family: monospace; }}
    a {{ text-decoration: underline; }}
    </style>
    </head>
    <body>
    <h2>Terminal Output</h2>
    <pre>{text}</pre>
    <a href='/'>Back</a>
    </body>
    </html>
    """)

# ---------------- Real Shell Execution ----------------
@app.route("/terminal_exec", methods=["POST"])
def terminal_exec():
    cmd = request.form.get("cmd", "")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout + result.stderr
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# ---------------- Main Entry ----------------
if __name__ == "__main__":
    emit_capsule_bios()
    app.run(host="0.0.0.0", port=8080, debug=True)

