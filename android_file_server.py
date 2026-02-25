#!/usr/bin/env python3
import http.server
import socketserver
import subprocess
import re
import os
import sys
import time
import cgi

PORT = 8000
SHARE_DIR = os.path.expanduser("~/lan-offline-share")

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")
VIDEO_EXT = (".mp4", ".webm", ".mkv", ".avi", ".mov")

os.makedirs(SHARE_DIR, exist_ok=True)
os.chdir(SHARE_DIR)

# ------------------ NETWORK ------------------

def get_wifi_iface():
    r = subprocess.run(["iw", "dev"], capture_output=True, text=True)
    for l in r.stdout.splitlines():
        if l.strip().startswith("Interface"):
            return l.split()[1]
    return None

def get_ip(iface):
    r = subprocess.run(
        ["ip", "-4", "addr", "show", iface],
        capture_output=True,
        text=True
    )
    m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", r.stdout)
    return m.group(1) if m else None

def show_qr(url):
    print("\n📱 Scan QR dari Android:\n")
    subprocess.run(["qrencode", "-t", "ANSIUTF8", url])

# ------------------ HTTP HANDLER ------------------

class Handler(http.server.SimpleHTTPRequestHandler):

    def do_POST(self):
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers["Content-Type"],
            }
        )

        if "file" not in form:
            self.send_error(400, "No file field")
            return

        files = form["file"]
        if not isinstance(files, list):
            files = [files]

        uploaded = 0
        for f in files:
            if not f.filename:
                continue

            name = os.path.basename(f.filename)
            with open(name, "wb") as out:
                out.write(f.file.read())

            print(f"[UPLOAD] {name}")
            uploaded += 1

        if uploaded == 0:
            self.send_error(400, "No valid files")
            return

        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()

    def list_directory(self, path):
        files = sorted(f for f in os.listdir(path) if not f.startswith("."))

        html = [
            "<html><head>",
            "<meta name='viewport' content='width=device-width, initial-scale=1'>",
            "<style>",
            "body{font-family:sans-serif;background:#0f172a;color:#e5e7eb;padding:10px}",
            "h2{text-align:center}",
            ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}",
            ".item{background:#020617;padding:8px;border-radius:10px;text-align:center}",
            "img,video{max-width:100%;max-height:130px;border-radius:6px}",
            "video{background:#000}",
            "a{color:#38bdf8;text-decoration:none;font-size:12px;word-break:break-all}",
            "form{margin-bottom:15px}",
            "</style></head><body>",

            "<h2>📂 Android ⇄ Ubuntu (LAN Offline)</h2>",

            "<form method=POST enctype=multipart/form-data>",
            "<input type=file name=file multiple>",
            "<br><br>",
            "<input type=submit value='Upload'>",
            "</form>",

            "<div class='grid'>"
        ]

        for n in files:
            low = n.lower()

            # 🖼 IMAGE
            if low.endswith(IMAGE_EXT):
                html.append(
                    f"<div class='item'>"
                    f"<a href='{n}'>"
                    f"<img src='{n}' loading='lazy'><br>{n}"
                    f"</a></div>"
                )

            # 🎬 VIDEO (player inline)
            elif low.endswith(VIDEO_EXT):
                base = os.path.splitext(n)[0]
                poster = ""
                for ext in IMAGE_EXT:
                    if base + ext in files:
                        poster = base + ext
                        break

                poster_attr = f"poster='{poster}'" if poster else ""

                html.append(
                    f"<div class='item'>"
                    f"<video src='{n}' {poster_attr} "
                    f"controls preload='metadata' muted playsinline></video>"
                    f"<div>{n}</div>"
                    f"</div>"
                )

            # 📄 OTHER FILES
            else:
                html.append(
                    f"<div class='item'>"
                    f"📄<br><a href='{n}'>{n}</a>"
                    f"</div>"
                )

        html.append("</div></body></html>")

        data = "\n".join(html).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

# ------------------ MAIN ------------------

def main():
    iface = get_wifi_iface()
    if not iface:
        print("❌ Wi-Fi interface tidak ditemukan")
        sys.exit(1)

    ip = None
    for _ in range(15):
        ip = get_ip(iface)
        if ip:
            break
        time.sleep(1)

    if not ip:
        print("❌ IP belum tersedia")
        sys.exit(1)

    url = f"http://{ip}:{PORT}"
    print(f"[READY] Share dir : {SHARE_DIR}")
    print(f"[READY] URL       : {url}")

    show_qr(url)

    with socketserver.TCPServer(("", PORT), Handler) as s:
        print("[SERVER] LAN offline server berjalan…")
        s.serve_forever()

if __name__ == "__main__":
    main()
