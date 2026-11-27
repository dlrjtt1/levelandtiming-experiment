#!/bin/sh
# Face-to-face runs (HD600 set, no headphone or volume screens): serves the page from this folder and opens it in lab mode.
# Close this window to stop. Answers go to the same sheet as the online runs (column "mode" = lab).
cd "$(dirname "$0")/web"
(sleep 1; open "http://localhost:8000/?mode=lab") &
python3 -m http.server 8000
