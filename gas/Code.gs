/**
 * Receiver for the pilot 2 experiment page (Google Apps Script web app, bound to a Google Sheet).
 *   POST (text/plain, JSON {session, trials, first_index, final})  -> rows in the sheets "trials" and "sessions", raw copy in "raw"
 *   GET  ?assign=1                                                 -> {"order": "LCR"}: the seat order used least so far (balanced)
 * Set-up: gas/README.md.  No personal data is stored: the page sends a random participant code only.
 */
var ORDERS = ["LCR", "LRC", "CLR", "CRL", "RLC", "RCL"];
var TRIAL_COLS = ["session_id", "index", "block", "seat", "rep", "n", "file", "hidden", "itdg_ms", "level_ratio_db",
                  "q1", "q1_hard", "q2", "q3", "plays", "listen_s", "rt_s", "at"];

function sheet_(name, header) {
  var ss = SpreadsheetApp.getActiveSpreadsheet(), sh = ss.getSheetByName(name);
  if (!sh) { sh = ss.insertSheet(name); sh.appendRow(header); sh.setFrozenRows(1); }
  return sh;
}

function doPost(e) {
  var lock = LockService.getScriptLock(); lock.waitLock(20000);
  try {
    var d = JSON.parse(e.postData.contents), s = d.session || {}, now = new Date();
    sheet_("raw", ["received", "session_id", "first_index", "final", "json"])
      .appendRow([now, s.session_id, d.first_index, d.final, e.postData.contents.slice(0, 49000)]);
    var tr = d.trials || [];
    if (tr.length) {
      var sh = sheet_("trials", ["received", "pid", "mode", "version"].concat(TRIAL_COLS));
      var rows = tr.map(function (t) {
        return [now, s.pid, s.mode, s.version].concat(TRIAL_COLS.map(function (c) { return t[c] === undefined || t[c] === null ? "" : t[c]; }));
      });
      sh.getRange(sh.getLastRow() + 1, 1, rows.length, rows[0].length).setValues(rows);
    }
    if (d.final) {   // one row per finished session; all session fields as JSON as well, so nothing is lost when fields are added
      sheet_("sessions", ["received", "session_id", "pid", "mode", "version", "lang", "seat_order", "n_trials_sent_last", "session_json"])
        .appendRow([now, s.session_id, s.pid, s.mode, s.version, s.lang, s.seat_order, tr.length, JSON.stringify(s).slice(0, 49000)]);
    }
    return out_({ ok: true, stored: tr.length });
  } catch (err) {
    return out_({ ok: false, error: String(err) });
  } finally { lock.releaseLock(); }
}

function doGet(e) {
  if (e && e.parameter && e.parameter.assign) {
    var lock = LockService.getScriptLock(); lock.waitLock(20000);
    try {
      var sh = sheet_("assign", ["given", "order"]), n = {};
      ORDERS.forEach(function (o) { n[o] = 0; });
      var v = sh.getLastRow() > 1 ? sh.getRange(2, 2, sh.getLastRow() - 1, 1).getValues() : [];
      v.forEach(function (r) { if (n[r[0]] !== undefined) n[r[0]]++; });
      var min = Math.min.apply(null, ORDERS.map(function (o) { return n[o]; }));
      var pool = ORDERS.filter(function (o) { return n[o] === min; });
      var order = pool[Math.floor(Math.random() * pool.length)];
      sh.appendRow([new Date(), order]);
      return out_({ order: order });
    } finally { lock.releaseLock(); }
  }
  return out_({ ok: true, service: "pilot2 receiver" });
}

function out_(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }
