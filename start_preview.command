#!/bin/sh
# Double-click: serves the experiment page from this folder and opens it in the browser. Close this window to stop.
cd "$(dirname "$0")/web"
(sleep 1; open "http://localhost:8000/?mode=online") &
python3 - <<'PY'
import http.server
class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()
    def log_message(self, *a): pass
print("Serving on http://localhost:8000  (close this window to stop)")
http.server.ThreadingHTTPServer(("127.0.0.1", 8000), H).serve_forever()
PY
