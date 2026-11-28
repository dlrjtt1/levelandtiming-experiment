"""Second, nastier stress test of the face-to-face (lab) page in headless Chrome.
usage: python tools/stress_lab2.py [names...]     e.g.  python tools/stress_lab2.py slow tabs     (no names = all)
Everything is local: one in-process server plays the page server (web/ + /sysvol) AND the receiver (/exec), so the
receiver can be slow, lie, hang or die, and the page server can die mid-session. Nothing reaches the real sheet.

  slow     receiver answers after 30 s: trials recorded while a transmission is in flight must still be sent
  lies     receiver answers HTTP 200 {"ok": false} (what the Apps Script does when the sheet write fails)
  hang     receiver never answers: the end screen must give up, say so, and offer "send again"
  tabs     the same session opened in a second tab: the old tab must stop, nothing lost or doubled
  storage  localStorage refuses every write
  dblclick double / triple clicks while the next sound is still loading (after a resume), and across two screens
  dblvol   slow /sysvol + double click on "volume set" must not skip the instructions
  input    hostile text in the code field (URL and typed), in free text; formula-looking code
  dies     page server dies during a block and comes back: block finishes, next block waits with "retry"
  corrupt  damaged saved sessions in localStorage must not give a blank page
  boot     design.json / language file cannot be loaded at start: message, not a blank page
  sizes    800x500, 640x400 (= 200 % zoom), portrait, 2560x1440: everything reachable, nothing cut, 3 languages
  monkey   random clicks, keys, typing, reloads for the whole (debug) session, then invariants
  monkey5  same without debug (5 s rule on) for a few minutes
"""
import http.server, json, os, random, re, sys, threading, time
from playwright.sync_api import sync_playwright

WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web")
PORT = int(os.environ.get("PORT", 8771))
ORIGIN = f"http://localhost:{PORT}"
fail, notes = [], []
SHOTS = "/tmp/stress2"; os.makedirs(SHOTS, exist_ok=True)
ARGS = ["--autoplay-policy=no-user-gesture-required"]


class World:
    """What the servers do right now; changed by the scenarios while the page runs."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.posts = []            # accepted transmissions (parsed)
        self.attempts = 0          # every POST that arrived
        self.recv = "ok"           # ok | down (500) | lies (200 ok:false) | hang
        self.delay = 0.0           # seconds before the receiver answers (non-final only if delay_final is False)
        self.delay_final = True
        self.vol, self.vol_delay = 55, 0.0
        self.dead = False          # page server refuses everything except the receiver
        self.missing = set()       # paths that answer 404
        self.audio_delay = 0.0     # seconds before a sound file is served
        self.timeout_s = None      # sendTimeoutS written into config.js
        self.release = threading.Event()


W = World()


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=WEB, **k)

    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store"); self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def _json(self, o, status=200):
        b = json.dumps(o).encode(); self.send_response(status); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/exec":
            return self._json({"order": "LRC"})
        if W.dead:
            return self.send_error(503)
        if path == "/sysvol":
            time.sleep(W.vol_delay); return self._json({"volume": W.vol, "muted": False})
        if path == "/config.js":      # same settings, receiver = this server
            s = open(os.path.join(WEB, "config.js"), encoding="utf-8").read()
            s = re.sub(r"https://script\.google\.com/macros/s/[\w-]+/exec", f"http://127.0.0.1:{PORT}/exec", s)
            if W.timeout_s is not None:
                s += f"\nwindow.P2_CONFIG.sendTimeoutS = {W.timeout_s};\n"
            b = s.encode(); self.send_response(200); self.send_header("Content-Type", "text/javascript"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b); return
        if any(m in path for m in W.missing):
            return self.send_error(404)
        if W.audio_delay and "/audio/" in path:
            time.sleep(W.audio_delay)
        try:
            super().do_GET()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0); raw = self.rfile.read(n); W.attempts += 1
        try:
            d = json.loads(raw)
        except Exception:
            return self._json({"ok": False, "error": "bad json"})
        try:
            if W.recv == "hang":
                W.release.wait(600); return
            if W.delay and (W.delay_final or not d.get("final")):
                time.sleep(W.delay)
            if W.recv == "down":
                return self._json({"x": 1}, 500)
            if W.recv == "lies":
                return self._json({"ok": False, "error": "Exception: Service Spreadsheets timed out"})
            W.posts.append(d); self._json({"ok": True, "stored": len(d.get("trials") or [])})
        except (BrokenPipeError, ConnectionResetError):
            pass


srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), H); srv.daemon_threads = True
threading.Thread(target=srv.serve_forever, daemon=True).start()


def ok(c, m):
    print(("ok   " if c else "FAIL ") + m, flush=True)
    if not c:
        fail.append(m)


def url(debug=True, lang="ja", extra=""):
    return f"{ORIGIN}/?mode=lab&lang={lang}" + ("&debug=1" if debug else "") + extra


def new_page(ctx, errs, u):
    p = ctx.new_page()
    p.on("pageerror", lambda e: errs.append(str(e)))
    p.on("dialog", lambda d: d.accept())
    p.goto(u)
    return p


def state(p):
    return p.evaluate("window.__p2 && window.__p2.state()")


def step_type(p):
    return p.evaluate("(() => { const s = window.__p2 && window.__p2.state(); return s ? window.__p2.steps()[s.idx].type : null; })()")


def consent(p, pid=None):
    p.wait_for_selector("#ok"); p.check("#ok"); p.check("#age")
    if pid is not None:
        p.fill("#pid", pid)
    p.click("#go")


def lr_check(p):
    p.wait_for_selector("#bl")
    for _ in range(80):
        if p.query_selector("#go"):
            break
        if p.query_selector("#pl") and p.is_enabled("#pl"):
            p.click("#pl")
        try:
            p.wait_for_selector("#bl:not([disabled])", timeout=1500); p.click(random.choice(["#bl", "#br"]))
        except Exception:
            pass
        p.wait_for_timeout(40)
    p.click("#go")


def volume(p, typed=None):
    p.wait_for_selector("#vs"); p.click("#pl")
    if typed is not None:
        p.fill("#vs", typed)
    p.wait_for_selector("#go:not([disabled])", timeout=8000); p.click("#go")


def instructions_quiz(p):
    p.wait_for_selector("table.grid"); p.click("#go")
    p.wait_for_selector(".quiz"); p.check("input[name=qz1][value='a']"); p.check("input[name=qz2][value='b']"); p.check("input[name=qz3][value='a']"); p.click("#go")


def front(p, pid=None):
    consent(p, pid); lr_check(p); volume(p); instructions_quiz(p)


def answer_trial(p):
    p.wait_for_selector("input[name=q1]:not([disabled])", timeout=20000)
    for q in ("q1", "q2", "q3"):
        p.click(f"label:has(input[name={q}][value='{random.randint(1, 5)}'])")
    p.wait_for_selector("#go:not([disabled])", timeout=20000); p.click("#go")


def fill_post(p):
    p.click("label:has(input[name=p1][value='3'])"); p.click("label:has(input[name=p3][value='2'])"); p.check("input[name=p5][value='no']")


def advance(p, stop_at_trial=True, post=None):
    """Go on until a recorded trial is on screen (returns 'trial') or the end screen ('end')."""
    for _ in range(300):
        p.wait_for_selector("#go, #dl, #pl, #y, #re", timeout=90000); p.wait_for_timeout(120)
        if p.query_selector("#dl"):
            return "end"
        if p.query_selector("#re"):
            return "error"
        if p.query_selector("#qs"):
            if step_type(p) == "trial" and p.evaluate("!!window.__p2.steps()[window.__p2.state().idx].practice"):
                answer_trial(p); continue
            if stop_at_trial:
                return "trial"
            answer_trial(p); continue
        if p.query_selector(".panel #pl"):
            p.click("#pl"); p.wait_for_selector("#go:not([disabled])", timeout=40000); p.click("#go"); continue
        if p.query_selector("input[name=p5]"):
            (post or fill_post)(p); p.click("#go"); continue
        p.wait_for_selector("#go:not([disabled])", timeout=60000); p.click("#go")
    return "stuck"


def finish(p, **k):
    while True:
        w = advance(p, **k)
        if w != "trial":
            return w
        answer_trial(p)


def received():
    return sorted(t["index"] for c in W.posts for t in c["trials"])


def browser(pw, **k):
    b = pw.chromium.launch(channel="chrome", args=ARGS)
    return b, b.new_context(viewport=k.pop("viewport", {"width": 1440, "height": 900}), **k)


# ---------------------------------------------------------------- scenarios
def slow(pw):
    """A transmission that takes 30 s is still in flight while the next block is being answered."""
    b, ctx = browser(pw); errs = []; W.delay, W.delay_final = 30, False
    p = new_page(ctx, errs, url()); front(p, "LSLOW")
    ok(finish(p) == "end", "slow receiver: reached the end screen")
    p.wait_for_selector("#dl"); p.wait_for_timeout(1500)
    S = state(p); got = received()
    ok(len(S["trials"]) == 12, "slow receiver: 12 trials stored")
    ok(sorted(set(got)) == list(range(1, 13)), f"slow receiver: every trial reached the receiver (got {sorted(set(got))})")
    ok(len(got) == len(set(got)), f"slow receiver: no trial sent twice ({len(got)} rows)")
    ok(not p.query_selector("p.warn"), "slow receiver: end screen reports success")
    ok(not errs, f"slow receiver: no page errors {errs[:2]}"); b.close()


def lies(pw):
    """HTTP 200 with ok:false = the sheet write failed. The page must not count that as sent."""
    b, ctx = browser(pw); errs = []; W.recv = "lies"
    p = new_page(ctx, errs, url()); front(p, "LLIES")
    ok(finish(p) == "end", "lying receiver: reached the end screen")
    p.wait_for_timeout(800)
    ok(p.query_selector("p.warn") is not None, "lying receiver: end screen says sending FAILED")
    ok(state(p)["sent"] == 0, f"lying receiver: nothing marked as sent (sent = {state(p)['sent']})")
    W.recv = "ok"
    if p.query_selector("#rs"):
        p.click("#rs"); p.wait_for_timeout(1000)
    ok(sorted(received()) == list(range(1, 13)) and not p.query_selector("p.warn"), f"lying receiver: 'send again' delivers all 12 ({received()})")
    ok(not errs, f"lying receiver: no page errors {errs[:2]}"); b.close()


def hang(pw):
    b, ctx = browser(pw); errs = []; W.timeout_s = 4
    p = new_page(ctx, errs, url()); front(p, "LHANG")
    n = 0
    while advance(p) == "trial":
        n += 1
        if n == 2:
            W.recv = "hang"
        answer_trial(p)
    t0 = time.time()
    try:
        p.wait_for_selector("#dl", timeout=20000); waited = time.time() - t0
        ok(True, "hanging receiver: end screen gives up (limit set to 4 s for the test)")
        ok(p.query_selector("p.warn") is not None and p.query_selector("#rs") is not None, "hanging receiver: failure message and 'send again' shown")
        W.recv = "ok"; W.release.set(); p.click("#rs"); p.wait_for_timeout(1500)
        ok(sorted(set(received())) == list(range(1, 13)) and not p.query_selector("p.warn"), f"hanging receiver: 'send again' delivers all 12 ({sorted(set(received()))})")
    except Exception:
        ok(False, "hanging receiver: end screen still says 'sending...' after 20 s (no time limit on the transmission)")
        p.screenshot(path=f"{SHOTS}/hang.png")
    W.release.set()
    ok(not errs, f"hanging receiver: no page errors {errs[:2]}"); b.close()


def tabs(pw):
    b, ctx = browser(pw); errs = []
    a = new_page(ctx, errs, url()); front(a, "LTABS")
    for _ in range(4):
        ok_ = advance(a) == "trial"; answer_trial(a)
    advance(a)                                                # tab A sits on trial 5
    b2 = new_page(ctx, errs, url()); b2.wait_for_selector("#y")
    txt = b2.inner_text("#app")
    ok("LTABS" in txt, "resume prompt names the participant code (so a left-over session of the previous person is recognisable)")
    b2.screenshot(path=f"{SHOTS}/resume_prompt.png")
    b2.click("#y"); b2.wait_for_timeout(600)
    locked = a.query_selector("#qs") is None
    ok(locked, "second tab resumed: the first tab stops showing the trial")
    a.screenshot(path=f"{SHOTS}/tab_superseded.png")
    if not locked:                                            # old behaviour: answer the same trial in both tabs
        answer_trial(a)
    ok(finish(b2) == "end", "second tab: reached the end screen"); b2.wait_for_timeout(800)
    S = state(b2); idx = [t["index"] for t in S["trials"]]
    ok(idx == list(range(1, 13)), f"two tabs: stored trials 1..12 once each (got {idx})")
    got = received()
    ok(sorted(set(got)) == list(range(1, 13)), f"two tabs: receiver has every trial ({sorted(set(got))})")
    ok(len(got) == len(set(got)), f"two tabs: no trial sent twice ({len(got)} rows for 12 trials)")
    sa = state(a)
    ok(sa is None or len(sa["trials"]) <= 4, "two tabs: the stopped tab recorded nothing more")
    ok(not errs, f"two tabs: no page errors {errs[:2]}"); b.close()


def storage(pw):
    b, ctx = browser(pw); errs = []
    ctx.add_init_script("Storage.prototype.setItem = function () { throw new DOMException('QuotaExceededError', 'QuotaExceededError'); };")
    p = new_page(ctx, errs, url()); front(p, "LSTORE")
    ok(finish(p) == "end", "storage refuses writes: reached the end screen"); p.wait_for_timeout(800)
    ok(received() == list(range(1, 13)) and not p.query_selector("p.warn"), "storage refuses writes: all 12 trials delivered")
    ok(not errs, f"storage refuses writes: no page errors {errs[:2]}"); b.close()
    b, ctx = browser(pw); errs = []                           # storage not available at all (blocked by a browser setting)
    ctx.add_init_script("Object.defineProperty(window, 'localStorage', { get() { throw new DOMException('SecurityError', 'SecurityError'); } });")
    W.posts = []
    p = new_page(ctx, errs, url())
    try:
        front(p, "LNOSTORE"); r = finish(p); p.wait_for_timeout(800)
        ok(r == "end" and received() == list(range(1, 13)), "storage blocked completely: session still runs and is delivered")
    except Exception as e:
        ok(False, f"storage blocked completely: page does not start ({str(e)[:80]})"); p.screenshot(path=f"{SHOTS}/nostorage.png")
    ok(not errs, f"storage blocked: no page errors {errs[:2]}"); b.close()


def dblvol(pw):
    b, ctx = browser(pw); errs = []; W.vol_delay = 0.4       # osascript on a real Mac takes a few hundred ms
    p = new_page(ctx, errs, url()); consent(p, "LDBL"); lr_check(p)
    p.wait_for_selector("#vs"); p.click("#pl"); p.wait_for_selector("#go:not([disabled])", timeout=8000)
    p.wait_for_timeout(900)
    p.dblclick("#go"); p.wait_for_timeout(1500)
    ok(step_type(p) == "instructions", f"double click on 'volume set' with a slow /sysvol lands on the instructions (now: {step_type(p)})")
    ok(state(p)["session"].get("volume_system") == 55, "volume_system recorded")
    ok(not errs, f"dblvol: no page errors {errs[:2]}"); b.close()


def dblclick(pw):
    """Double clicks while the next screen is still loading its sound (slow disk / after a resume nothing is preloaded)."""
    b, ctx = browser(pw); errs = []
    p = new_page(ctx, errs, url()); front(p, "LDBLC")
    W.audio_delay = 0.6
    p.wait_for_selector("#go"); ok(step_type(p) == "practiceIntro", "at the practice intro")
    p.dblclick("#go"); p.wait_for_timeout(2500)
    i0 = state(p)["idx"]
    ok(p.evaluate("window.__p2.steps()[window.__p2.state().idx].n") == 1, "double click on 'start practice' while the sound loads: practice 1 is shown, not skipped")
    while advance(p) != "trial":
        pass
    answer_trial(p); advance(p); answer_trial(p); advance(p)       # 2 trials stored, third on screen
    p.reload(); p.wait_for_selector("#y"); p.dblclick("#y"); p.wait_for_timeout(2500)
    ok(len(state(p)["trials"]) == 2 and p.query_selector("#qs") is not None, "double click on 'continue' after a reload: one trial screen, nothing stored")
    p.wait_for_selector("input[name=q1]:not([disabled])", timeout=20000)
    for q in ("q1", "q2", "q3"):
        p.click(f"label:has(input[name={q}][value='3'])")
    p.wait_for_selector("#go:not([disabled])", timeout=20000)
    p.click("#go", click_count=3, delay=40); p.wait_for_timeout(2500)
    tr = state(p)["trials"]
    ok([t["index"] for t in tr] == [1, 2, 3], f"triple click on 'next' while the next sound loads: stored once ({[t['index'] for t in tr]})")
    W.audio_delay = 0
    ok(finish(p) == "end", "double clicks: reached the end"); p.wait_for_timeout(800)
    tr = state(p)["trials"]; got = received()
    ok([t["index"] for t in tr] == list(range(1, 13)) and sorted(got) == list(range(1, 13)), f"double clicks: trials 1..12 stored and received once each ({[t['index'] for t in tr]})")
    ok(not errs, f"double clicks: no page errors {errs[:2]}"); b.close()
    b, ctx = browser(pw); errs = []                           # double click that would run through two screens whose buttons sit in the same place
    p = new_page(ctx, errs, url()); consent(p, "LDBLC2"); lr_check(p)
    p.wait_for_selector("#vs"); p.click("#pl"); p.wait_for_selector("#go:not([disabled])", timeout=8000); p.wait_for_timeout(900)
    for _ in range(6):                                        # volume -> instructions -> (quiz); break and practice-end screens later
        if step_type(p) != "volume":
            break
        box = p.eval_on_selector("#go", "e => { const r = e.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }")
        p.mouse.click(box[0], box[1], click_count=2, delay=60); p.wait_for_timeout(700)
    ok(step_type(p) == "instructions", f"fast double click on 'volume set': instructions are shown, not skipped (now: {step_type(p)})")
    b.close()


EVIL = "\"><img src=x onerror=\"window.__pwned=1\"><script>window.__pwned=2</script>"


def inputs(pw):
    b, ctx = browser(pw); errs = []
    from urllib.parse import quote
    p = new_page(ctx, errs, url(extra="&pid=" + quote(EVIL))); p.wait_for_selector("#pid"); p.wait_for_timeout(300)
    ok(p.evaluate("window.__pwned") is None and p.query_selector("#app img") is None, "code from the URL cannot inject HTML into the consent screen")
    ok(p.query_selector("#go") is not None and p.query_selector("#age") is not None, "consent screen intact with a hostile ?pid=")
    p.check("#ok"); p.check("#age"); p.fill("#pid", "=HYPERLINK(\"http://x\",\"a b\")/../😀 한글"); p.click("#go")
    pid = state(p)["session"]["pid"]
    ok(not pid.startswith(("=", "+", "-", "@")) and re.fullmatch(r"[\w-]+", pid, re.A) is not None, f"typed code is reduced to letters/digits/-/_ (stored: {pid!r}), so the sheet cannot read it as a formula")
    lr_check(p); volume(p, typed="<b>62%</b> \"x\""); instructions_quiz(p)
    long = "あ" * 5000 + "</textarea><script>window.__pwned=3</script>"

    def post(p):
        fill_post(p); p.fill("#p2o", EVIL); p.fill("#p6", long); p.fill("#p4", "-5")
    ok(finish(p, post=post) == "end", "hostile inputs: reached the end screen"); p.wait_for_timeout(800)
    S = state(p)["session"]
    ok(p.evaluate("window.__pwned") is None, "no injected script ran anywhere in the session")
    ok(S["volume_setting"] == "<b>62%</b> \"x\"" and S["post"]["unstable_other"] == EVIL[:200] and len(S["post"]["comments"]) == 2000, "free text is stored as typed (length limits 200 / 2000 hold)")
    ok(W.posts and W.posts[-1]["final"] and W.posts[-1]["session"]["post"]["comments"] == S["post"]["comments"], "free text arrives unchanged at the receiver")
    notes.append(f"experience_years typed as -5 is stored as {S['post']['experience_years']!r}")
    ok(not errs, f"hostile inputs: no page errors {errs[:2]}"); b.close()
    b, ctx = browser(pw); errs = []                           # code made only of characters that are removed
    p = new_page(ctx, errs, url()); p.wait_for_selector("#pid"); p.check("#ok"); p.check("#age"); p.fill("#pid", "한글 😀 !!")
    ok(p.is_disabled("#go") or True, "-")
    if not p.is_disabled("#go"):
        p.click("#go"); p.wait_for_timeout(200)
    st = state(p)
    ok(st["idx"] == 0 or st["session"]["pid"] != "", f"a code with no usable characters is not accepted as empty (idx {st['idx']}, pid {st['session']['pid']!r})")
    b.close()


def dies(pw):
    b, ctx = browser(pw); errs = []
    p = new_page(ctx, errs, url(extra="&order=LRC")); front(p, "LDIES")       # L first: 3 trials in the first block (debug)
    ok(advance(p) == "trial", "server dies: first recorded trial reached")
    W.dead = True                                             # the terminal window was closed
    w = None
    for _ in range(3):                                        # the 3 trials of the first block are already in memory
        answer_trial(p); w = advance(p)
        if w != "trial":
            break
    ok(len(state(p)["trials"]) == 3, f"server dies: the running block is finished from memory ({len(state(p)['trials'])} of 3)")
    ok(w == "error", f"server dies: next block shows the load error with 'retry' (got {w})")
    p.screenshot(path=f"{SHOTS}/server_dead.png")
    if w == "error":
        p.click("#re"); p.wait_for_timeout(800)
        ok(p.query_selector("#re") is not None, "server still dead: 'retry' shows the error again (no crash)")
        W.dead = False; p.click("#re")
    ok(finish(p) == "end", "server back: 'retry' continues to the end"); p.wait_for_timeout(800)
    ok(sorted(set(received())) == list(range(1, 13)), "server dies: all 12 trials delivered")
    ok(not errs, f"server dies: no page errors {errs[:2]}"); b.close()
    b, ctx = browser(pw); errs = []; W.posts = []             # same, but the page is reloaded while the server is dead, then again when it is back
    p = new_page(ctx, errs, url()); front(p, "LDIES2"); advance(p); answer_trial(p); advance(p)
    W.dead = True
    try:
        p.reload(timeout=5000)
    except Exception:
        pass
    W.dead = False; p.goto(url()); p.wait_for_selector("#y"); p.click("#y")
    ok(len(state(p)["trials"]) == 1, "reload while the server is dead, reopen when it is back: session resumes with its stored trial")
    ok(finish(p) == "end" and sorted(set(received())) == list(range(1, 13)), "…and finishes with all 12 trials delivered")
    b.close()


def corrupt(pw):
    cases = {"not json": "{oops", "null": "null", "number": "42", "empty object": "{}", "array": "[]",
             "no idx/trials": json.dumps({"done": False, "session": {"debug": True, "version": "pilot2-0.4", "lang": "ja"}}),
             "bad lang": json.dumps({"idx": 3, "sent": 0, "done": False, "trials": [], "session": {"debug": True, "version": "pilot2-0.4", "lang": "xx", "seat_order": "LCR", "seed": 1}}),
             "idx beyond end": json.dumps({"idx": 999, "sent": 0, "done": False, "trials": [], "session": {"debug": True, "version": "pilot2-0.4", "lang": "ja", "seat_order": "LCR", "seed": 1, "session_id": "ab"}}),
             "bad seat order": json.dumps({"idx": 2, "sent": 0, "done": False, "trials": [], "session": {"debug": True, "version": "pilot2-0.4", "lang": "ja", "seat_order": "XYZ", "seed": 1, "session_id": "ab"}}),
             "trials not a list": json.dumps({"idx": 2, "sent": 0, "done": False, "trials": "x", "session": {"debug": True, "version": "pilot2-0.4", "lang": "ja", "seat_order": "LCR", "seed": 1, "session_id": "ab"}})}
    b, _ = browser(pw)
    for name, val in cases.items():
        ctx = b.new_context(); errs = []
        ctx.add_init_script("if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1'); localStorage.setItem('levelandtiming_session_lab', %s); }" % json.dumps(val))
        p = new_page(ctx, errs, url()); p.wait_for_timeout(700)
        if p.query_selector("#y"):
            p.click("#y"); p.wait_for_timeout(700)
        alive = p.evaluate("document.querySelector('#app').innerText.trim().length") > 20 and p.query_selector("#app button") is not None
        ok(alive and not errs, f"damaged saved session ({name}): page shows something usable, no error {errs[:1]}")
        if not alive:
            p.screenshot(path=f"{SHOTS}/corrupt_{name.replace(' ', '_').replace('/', '_')}.png")
        ctx.close()
    b.close()


def boot(pw):
    for what in ("design.json", "i18n/ja.json"):
        b, ctx = browser(pw); errs = []; W.missing = {what}
        p = new_page(ctx, errs, url()); p.wait_for_timeout(900)
        n = p.evaluate("document.querySelector('#app').innerText.trim().length")
        ok(n > 10, f"{what} cannot be loaded: the page says so instead of staying blank (text length {n})")
        W.missing = set()
        if p.query_selector("#app button"):
            p.click("#app button"); p.wait_for_timeout(900)
            ok(p.query_selector("#ok") is not None, f"{what} back: the reload button leads to the consent screen")
        b.close()


def sizes(pw):
    b, _ = browser(pw)
    check = """() => {
      const out = []; const vw = innerWidth, vh = innerHeight;
      if (document.scrollingElement.scrollWidth > vw + 1) out.push('page scrolls sideways: ' + document.scrollingElement.scrollWidth + ' > ' + vw);
      const els = [...document.querySelectorAll('#app button, #app .scale label, #app .dk, #app input[type=text], #app textarea, #app .end, #app .t')];
      for (const e of els) {
        e.scrollIntoView({ block: 'center' }); const r = e.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) continue;
        if (r.left < -1 || r.right > vw + 1) out.push('cut horizontally: ' + (e.id || e.className || e.tagName) + ' ' + Math.round(r.left) + '..' + Math.round(r.right));
        if (r.top < -1 || r.bottom > vh + 1) { if (r.height <= vh) out.push('cannot be scrolled into view: ' + (e.id || e.className || e.tagName)); }
        if (e.matches('button, label')) { const x = r.left + r.width / 2, y = r.top + r.height / 2, h = document.elementFromPoint(x, y); if (h && !(e.contains(h) || h.contains(e))) out.push('covered: ' + (e.id || e.className || e.tagName) + ' by ' + (h.id || h.className || h.tagName)); }
      }
      const ends = [...document.querySelectorAll('#app .scale')].flatMap((s) => { const d = s.querySelector('.dots').getBoundingClientRect(); return [...s.querySelectorAll('.end')].map((e) => { const r = e.getBoundingClientRect(); return r.right > d.left + 1 && r.left < d.right - 1 && r.bottom > d.top + 1 && r.top < d.bottom - 1; }); });
      if (ends.some(Boolean)) out.push('scale end label overlaps the numbers');
      return out; }"""
    for lang in ("ja", "ko", "en"):
        ctx = b.new_context(viewport={"width": 1440, "height": 900}); errs = []
        p = new_page(ctx, errs, url(lang=lang)); bad = []
        visited = set()

        def look(tag):
            for w, h in ((800, 500), (640, 400), (768, 1024), (2560, 1440), (1280, 600)):
                p.set_viewport_size({"width": w, "height": h}); p.wait_for_timeout(120)
                r = p.evaluate(check)
                if r:
                    bad.append(f"{tag} {w}x{h}: {r[:3]}"); p.screenshot(path=f"{SHOTS}/size_{lang}_{tag}_{w}x{h}.png")
            p.set_viewport_size({"width": 1440, "height": 900})
        for _ in range(60):
            p.wait_for_selector("#go, #dl, #pl", timeout=60000); p.wait_for_timeout(250)
            ty = step_type(p)
            if ty == "trial":
                p.wait_for_selector("input[name=q1]:not([disabled])", timeout=20000)
            if ty not in visited:
                visited.add(ty); look(ty)
            if ty == "end":
                break
            if ty == "consent":
                consent(p, "LSIZE")
            elif ty == "lrcheck":
                lr_check(p)
            elif ty == "volume":
                volume(p)
            elif ty == "quiz":
                p.check("input[name=qz1][value='a']"); p.check("input[name=qz2][value='b']"); p.check("input[name=qz3][value='a']"); p.click("#go")
            elif ty == "trial":
                answer_trial(p)
            elif ty == "seat":
                p.click("#pl"); p.wait_for_selector("#go:not([disabled])", timeout=40000); p.click("#go")
            elif ty == "post":
                fill_post(p); p.click("#go")
            else:
                p.click("#go")
        ok(len(visited) >= 12, f"sizes {lang}: every kind of screen visited ({len(visited)})")
        ok(not bad, f"sizes {lang}: 5 window sizes x {len(visited)} screens, everything reachable, nothing cut or covered" + ("".join("\n       " + x for x in bad[:12]) if bad else ""))
        ok(not errs, f"sizes {lang}: no page errors {errs[:2]}"); ctx.close()
    b.close()


KEYS = ["Enter", "Space", "Tab", "Shift+Tab", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Escape", "Backspace", "1", "5", "a", "PageDown", "Home", "End"]


def monkey_run(pw, debug, seconds, seed):
    rnd = random.Random(seed)
    b, ctx = browser(pw, viewport={"width": 1280, "height": 760}); errs = []
    # watch from inside the page (every 2 ms): a step may only follow a user input, and one input may move one step
    ctx.add_init_script("""(() => { let ev = 0, last = null, lastEv = -1; const bad = () => JSON.parse(sessionStorage.getItem('__viol') || '[]');
      for (const k of ['click', 'keydown', 'change', 'input']) addEventListener(k, () => { ev++; }, true);
      setInterval(() => { const s = window.__p2 && window.__p2.state(); if (!s) return; const i = s.idx;
        if (last !== null && i !== last) { if (i !== last + 1 || ev === lastEv) { const v = bad(); v.push([last, i, ev === lastEv ? 'no input between' : 'jump']); sessionStorage.setItem('__viol', JSON.stringify(v)); } lastEv = ev; }
        last = i; }, 2); })();""")
    u = url(debug=debug); p = new_page(ctx, errs, u)
    t_end = time.time() + seconds; acts = 0; reloads = 0; last_idx = -1; jumps = []; helped = 0; last_move = time.time()
    while time.time() < t_end:
        if p.query_selector("#dl") and not p.query_selector("#rs"):
            break
        try:
            if p.query_selector("#y"):                        # resume prompt after a reload: always continue
                p.click("#y"); p.wait_for_timeout(150); continue
            r = rnd.random()
            if r < 0.62:                                      # click any control, enabled or not
                els = p.query_selector_all("#app button, #app label, #app input, #app textarea, #app .panel, #app h1")
                if els:
                    e = rnd.choice(els)
                    try:
                        e.click(force=True, timeout=300, no_wait_after=True, click_count=rnd.choice([1, 1, 1, 2, 3]))
                    except Exception:
                        pass
            elif r < 0.80:
                p.keyboard.press(rnd.choice(KEYS))
            elif r < 0.88:
                p.keyboard.type(rnd.choice(["abc", "12", " ", "<b>", "あ", "=1+1", "'\""]))
            elif r < 0.93:
                p.mouse.click(rnd.randint(0, 1279), rnd.randint(0, 759), click_count=rnd.choice([1, 2]))
            elif r < 0.955:
                p.set_viewport_size({"width": rnd.choice([900, 1100, 1280, 1500]), "height": rnd.choice([600, 760, 900])})
            elif r < 0.965 and reloads < 12:
                reloads += 1; p.reload(); p.wait_for_selector("#y, #ok, #app button", timeout=15000)
            else:
                p.wait_for_timeout(rnd.randint(50, 600))
            acts += 1
            s = state(p)
            if s:
                if s["idx"] != last_idx:
                    if last_idx >= 0 and s["idx"] != last_idx + 1:
                        jumps.append((last_idx, s["idx"]))
                    last_idx = s["idx"]; last_move = time.time()
                elif time.time() - last_move > (12 if debug else 25):   # the monkey is stuck: do what the screen asks, once
                    helped += 1; last_move = time.time(); ty = step_type(p)
                    try:
                        if ty == "consent":
                            consent(p, None if p.input_value("#pid").strip() else "LMONKEY")
                        elif ty == "lrcheck":
                            lr_check(p)
                        elif ty == "volume":
                            p.fill("#vs", "50"); p.click("#pl") if p.inner_text("#pl") and not p.is_enabled("#go") else None; p.wait_for_selector("#go:not([disabled])", timeout=6000); p.click("#go")
                        elif ty == "quiz":
                            p.check("input[name=qz1][value='a']"); p.check("input[name=qz2][value='b']"); p.check("input[name=qz3][value='a']"); p.click("#go")
                        elif ty == "trial":
                            # not playing (bar at 0) and either never started or stopped before the minimum listening time: play
                            if p.evaluate("(() => { const g = document.querySelector('#go'), b = document.querySelector('#pb'); return parseFloat(b.style.width || '0') === 0 && (/[0-9]/.test(g.textContent) || document.querySelector('#qs.locked') !== null); })()"):
                                p.click("#pl")
                            answer_trial(p)
                        elif ty == "seat":
                            if p.is_enabled("#pl"):
                                p.click("#pl")
                            p.wait_for_selector("#go:not([disabled])", timeout=40000); p.click("#go")
                        elif ty == "post":
                            fill_post(p); p.click("#go")
                        elif p.query_selector("#go"):
                            p.click("#go", timeout=3000)
                        s2 = state(p)                         # count the step the helper made, so it is not added to the next random action
                        if s2 and s2["idx"] == last_idx + 1:
                            last_idx = s2["idx"]
                    except Exception as e:
                        if os.environ.get("TRACE"):
                            print("  help failed at", ty, str(e)[:160].replace("\n", " "), "|", p.evaluate("document.querySelector('#app').innerText.slice(0,200)").replace("\n", " / "), "| pl:", p.evaluate("(() => { const b = document.querySelector('#pl'); return b ? b.textContent + (b.disabled ? ' [disabled]' : '') : null; })()"), "| ac:", p.evaluate("document.querySelectorAll('#qs input:disabled').length"), flush=True)
                            p.screenshot(path=f"{SHOTS}/stuck_{seed}_{helped}.png")
        except Exception as e:
            if "closed" in str(e):
                raise
    p.wait_for_timeout(1200)
    S = state(p); tr = S["trials"]; tag = f"monkey ({'debug' if debug else '5 s rule'}, seed {seed})"
    notes.append(f"{tag}: {acts} random actions, {reloads} reloads, helped {helped}x when stuck, reached step {S['idx']} / {p.evaluate('window.__p2.steps().length') - 1}, {len(tr)} trials")
    ok(not errs, f"{tag}: no page errors {errs[:3]}")
    viol = json.loads(p.evaluate("sessionStorage.getItem('__viol') || '[]'"))
    ok(not viol, f"{tag}: watched from inside the page, no screen was skipped and no input moved two steps {viol[:5]}")
    if jumps:
        notes.append(f"{tag}: the outside sampler saw {jumps[:4]} (two steps between two samples; the in-page watch is the check)")
    ok([t["index"] for t in tr] == list(range(1, len(tr) + 1)), f"{tag}: trial indices 1..{len(tr)} with no gap or repeat")
    ok(all(t[q] in (1, 2, 3, 4, 5) for t in tr for q in ("q1", "q2", "q3")), f"{tag}: every stored trial has all three answers in 1..5")
    mn = 1 if debug else 5
    short = [(t["index"], t["listen_s"]) for t in tr if t["listen_s"] < mn - 0.15]
    ok(not short, f"{tag}: no trial stored with less than {mn} s of listening {short[:5]}")
    ok(all(t["plays"] >= 1 and t["rt_s"] > 0 for t in tr), f"{tag}: plays >= 1 and response time > 0 in every trial")
    ses = S["session"]
    if S["idx"] > 0:
        ok(bool(ses.get("consent_at")) and bool(ses.get("pid")) and re.fullmatch(r"[\w-]+", ses["pid"], re.A) is not None, f"{tag}: past the consent screen only with consent and a clean code ({ses.get('pid')!r})")
    if S["idx"] > 2:
        ok(bool(ses.get("volume_setting")), f"{tag}: past the volume screen only with a volume setting ({ses.get('volume_setting')!r})")
    if S["idx"] > 4:
        ok(ses.get("quiz_attempts", 0) >= 1, f"{tag}: past the quiz only after passing it")
    got = received()
    ok(len(got) == len(set(got)) and set(got) <= set(range(1, len(tr) + 1)), f"{tag}: receiver has no doubled or unknown trial ({len(got)} rows)")
    if p.query_selector("#dl"):
        ok(sorted(got) == list(range(1, len(tr) + 1)) and W.posts[-1]["final"], f"{tag}: finished, and the receiver has all {len(tr)} trials")
        ok(ses.get("post", {}).get("hearing_problem") in ("yes", "no", "dk"), f"{tag}: finished only with the required end questions answered")
    b.close()


def monkey(pw):
    for seed in [int(x) for x in os.environ.get("SEEDS", "1,2,3").split(",")]:
        W.reset(); monkey_run(pw, True, int(os.environ.get("MONKEY_S", 240)), seed)


def monkey5(pw):
    monkey_run(pw, False, 300, 7)


ALL = {"dblclick": dblclick, "slow": slow, "lies": lies, "hang": hang, "tabs": tabs, "storage": storage, "dblvol": dblvol, "input": inputs, "dies": dies,
       "corrupt": corrupt, "boot": boot, "sizes": sizes, "monkey": monkey, "monkey5": monkey5}
want = [a for a in sys.argv[1:] if a in ALL] or list(ALL)
with sync_playwright() as pw:
    for name in want:
        print(f"\n== {name} ==", flush=True); W.reset()
        try:
            ALL[name](pw)
        except Exception as e:
            ok(False, f"{name} crashed: {e!r}"[:400])
print("\nnotes:"); [print(" -", n) for n in notes]
print("FAILED: %d" % len(fail) if fail else "stress test 2 passed")
for f in fail:
    print("  x", f[:200])
sys.exit(1 if fail else 0)
