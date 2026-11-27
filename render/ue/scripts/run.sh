#!/bin/sh
# sh run.sh <id> <script.py> [args...]  -> queue a script for the editor's watcher and wait for its output
D="$(cd "$(dirname "$0")" && pwd)"; id="$1"; s="$2"; shift 2
python3 - "$D" "$id" "$s" "$@" <<'PY'
import sys, json
D, id, s, *a = sys.argv[1:]
MAC = "/Users/user/Library/Mobile Documents/com~apple~CloudDocs/LABO 1557/UE_CR3_pilot2/"
body = "import sys, runpy\nsys.argv = " + json.dumps([s] + a) + "\nrunpy.run_path(" + json.dumps(MAC + s) + ", run_name='__main__')\n"
open(D + "/_cmd/" + id + ".py", "w").write(body)
PY
i=0; while [ ! -f "$D/_log/$id.out" ] && [ $i -lt ${WAIT:-60} ]; do sleep 1; i=$((i+1)); done
cat "$D/_log/$id.out" 2>/dev/null || echo "(no output yet)"
