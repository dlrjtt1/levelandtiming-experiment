# Google Apps Script receiver (online runs)

1. Make a new Google Sheet (any name). Extensions → Apps Script. Replace the editor's content with `Code.gs`. Save.
2. Deploy → New deployment → type "Web app". Execute as: **Me**. Who has access: **Anyone**. Deploy and allow the requested access
   (the script only writes to this sheet).
3. Copy the web-app URL (ends in `/exec`) into `web/config.js`:
   `online: { audioBase: "audio/online", ext: "flac", endpoint: "<URL>", assign: "<URL>?assign=1" }`
4. Test: open the page with `?debug=1`, finish a run, and check the sheets `raw`, `trials`, `sessions`, `assign`.
   After changing `Code.gs`: Deploy → Manage deployments → edit → version "New version" (the URL stays the same).

Sheets: `trials` one row per rated sound (sent at the end of each seat and at the end); `sessions` one row per finished session with all
session fields as JSON (headphones, left-right check, comprehension check, final questions); `raw` every request as received;
`assign` the seat orders handed out (the least-used order is given next, so the six orders stay balanced, also for unfinished runs).
If sending fails the page offers the result file for download; `tools/results_to_csv.py` reads those files.
Notes: Apps Script answers through a redirect and does not report errors by HTTP status; the page treats an answered request as stored.
A cell holds at most 50,000 characters: `raw`/`session_json` are cut at 49,000 (a session's fields are far below that).
