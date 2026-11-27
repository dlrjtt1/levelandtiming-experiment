#!/bin/sh
# Double-click: serves the experiment page from this folder and opens it in the browser. Close this window to stop.
cd "$(dirname "$0")/web"
(sleep 1; open "http://localhost:8000/?mode=online") &
python3 -m http.server 8000
