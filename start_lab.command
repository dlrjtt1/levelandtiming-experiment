#!/bin/sh
# Face-to-face runs (HD600 set, no headphone or volume screens): serves the page from this folder and opens it in lab mode.
# Close this window to stop. Answers go to the same sheet as the online runs (column "mode" = lab).
cd "$(dirname "$0")/web"
(sleep 1; open "http://localhost:8000/?mode=lab") &
python3 - <<'PY'
import http.server, json, subprocess
class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()
    def do_GET(self):
        if self.path.split("?")[0] == "/sysvol":   # macOS output volume (0-100) for the volume screen in lab mode
            try:
                o = subprocess.run(["osascript", "-e", "set v to get volume settings", "-e", "return (output volume of v as text) & \",\" & (output muted of v as text)"], capture_output=True, text=True, timeout=3).stdout.strip().split(",")
                body = json.dumps({"volume": int(o[0]), "muted": o[1].strip() == "true"})
            except Exception:
                body = json.dumps({"volume": None})
            b = body.encode(); self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b); return
        super().do_GET()
    def log_message(self, *a): pass
print("Serving on http://localhost:8000  (close this window to stop)")
http.server.ThreadingHTTPServer(("127.0.0.1", 8000), H).serve_forever()
PY
