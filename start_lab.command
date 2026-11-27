#!/bin/sh
# Face-to-face runs (HD600 set, no headphone or volume screens): serves the page from this folder and opens it in lab mode.
# Close this window to stop. Answers go to the same sheet as the online runs (column "mode" = lab).
cd "$(dirname "$0")/web"
(sleep 1; open "http://localhost:8000/?mode=lab") &
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
