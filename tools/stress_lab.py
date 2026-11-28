"""Stress test of the face-to-face (lab) page in headless Chrome: odd things a participant or experimenter might do.
usage: python tools/stress_lab.py [--quick]   (serves web/ itself; needs playwright and web/audio/lab/*)
The receiver is mocked (nothing reaches the real sheet); /sysvol (Mac volume) is mocked too.

Scenarios
  S1  full run without debug (64 trials): wrong left/right answers, volume read from /sysvol and changed during the session,
      click "next" before 5 s, double-click "next", reload mid-block (resume), close the tab and reopen (resume),
      receiver down for one block then back, small window. Checks every trial is stored and sent exactly once.
  S2  one sound file missing -> error screen with the reason -> file back -> "retry" continues
  S3  resume prompt -> "start over" gives a new session and clears the saved one
  S4  end screen reached with the receiver down -> failure message, download holds everything, "send again" works once it is back
"""
import json, os, random, subprocess, sys, time
from playwright.sync_api import sync_playwright

QUICK = "--quick" in sys.argv
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web")
srv = subprocess.Popen([sys.executable, "-m", "http.server", "8766", "--directory", root], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
BASE = "http://localhost:8766/?mode=lab&lang=ja"
fail, notes = [], []
SHOTS = "/tmp/stress"; os.makedirs(SHOTS, exist_ok=True)


def ok(c, m):
    print(("ok   " if c else "FAIL ") + m)
    if not c:
        fail.append(m)


class Mock:
    """Receiver + Mac volume. down=True makes the receiver answer 500."""
    def __init__(self):
        self.posts, self.down, self.vol = [], False, 55

    def attach(self, ctx):
        def gas(route):
            r = route.request
            if r.method == "POST":
                if self.down:
                    return route.fulfill(status=500, body="down", headers={"Access-Control-Allow-Origin": "*"})
                self.posts.append(json.loads(r.post_data))
                return route.fulfill(json={"ok": True}, headers={"Access-Control-Allow-Origin": "*"})
            return route.fulfill(json={"order": "LRC"}, headers={"Access-Control-Allow-Origin": "*"})
        ctx.route("https://script.google.com/**", gas)
        ctx.route("**/sysvol*", lambda route: route.fulfill(json={"volume": self.vol, "muted": False}))


def new_page(ctx, errs, url=BASE):
    p = ctx.new_page()
    p.on("pageerror", lambda e: errs.append(str(e)))
    p.on("dialog", lambda d: d.accept())
    p.goto(url)
    return p


def consent(p, pid):
    p.wait_for_selector("#ok"); ok(p.is_disabled("#go"), "consent: next disabled before both ticks")
    p.check("#ok"); ok(p.is_disabled("#go"), "consent: one tick is not enough (18+ missing)")
    p.check("#age"); p.fill("#pid", pid); p.click("#go")


def lr_check(p, wrong_first=True):
    p.wait_for_selector("#bl")
    if wrong_first:                                           # mash both answer buttons at once
        p.click("#pl"); p.click("#bl"); p.click("#br", force=True)
    for _ in range(80):
        if p.query_selector("#go"):
            break
        if p.is_enabled("#pl"):
            p.click("#pl")
        try:
            p.wait_for_selector("#bl:not([disabled])", timeout=1500); p.click(random.choice(["#bl", "#br"]))
        except Exception:
            pass
        p.wait_for_timeout(50)
    p.click("#go")


def volume(p, mock):
    p.wait_for_selector("#vs"); p.click("#pl")
    p.wait_for_timeout(1600); first = p.input_value("#vs")
    mock.vol = 62; p.wait_for_timeout(1600); second = p.input_value("#vs")
    ok(first == "mac 55" and second == "mac 62", f"volume field follows the Mac volume ({first!r} -> {second!r})")
    p.wait_for_selector("#go:not([disabled])", timeout=8000); p.click("#go")


def instructions_quiz(p):
    p.wait_for_selector("table.grid"); p.click("#go")
    p.wait_for_selector(".quiz"); p.check("input[name=qz1][value='b']"); p.check("input[name=qz2][value='a']"); p.check("input[name=qz3][value='b']"); p.click("#go")
    p.wait_for_timeout(200); p.check("input[name=qz1][value='a']"); p.check("input[name=qz2][value='b']"); p.check("input[name=qz3][value='a']"); p.click("#go")


def answer_trial(p, early_check=False, double=False):
    p.wait_for_selector("input[name=q1]:not([disabled])", timeout=20000)
    for q in ("q1", "q2", "q3"):
        p.click(f"label:has(input[name={q}][value='{random.randint(1, 5)}'])")
    if early_check:
        ok(p.is_disabled("#go"), "trial: next stays locked before the minimum listening time")
    p.wait_for_selector("#go:not([disabled])", timeout=20000)
    if double:
        p.dblclick("#go")
    else:
        p.click("#go")


def state(p):
    return p.evaluate("window.__p2.state()")


def step_until_trial_or_end(p):
    """Click through practice intro, practice trials, seat screens, breaks and the post questionnaire until a recorded trial or the end."""
    for _ in range(200):
        p.wait_for_selector("#go, #dl, #pl, #y", timeout=60000); p.wait_for_timeout(250)
        if p.query_selector("#dl"):
            return "end"
        if p.query_selector("#qs"):
            if p.evaluate("(() => { const s = window.__p2.state(); return !!window.__p2.steps()[s.idx].practice; })()"):
                answer_trial(p); continue
            return "trial"
        if p.query_selector(".panel #pl") and not p.query_selector("#qs"):
            p.click("#pl"); p.wait_for_selector("#go:not([disabled])", timeout=40000); p.click("#go"); continue
        if p.query_selector("input[name=p5]"):
            p.click("label:has(input[name=p1][value='3'])"); p.click("label:has(input[name=p3][value='2'])"); p.check("input[name=p2][value='a']")
            p.fill("#p4", "3"); p.check("input[name=p5][value='no']"); p.click("#go"); continue
        p.wait_for_selector("#go:not([disabled])", timeout=60000); p.click("#go")
    return "stuck"


def s1(pw):
    print("\n== S1 full lab run with odd behaviour ==")
    b = pw.chromium.launch(channel="chrome", args=["--autoplay-policy=no-user-gesture-required"])
    ctx = b.new_context(viewport={"width": 1440, "height": 900}); mock = Mock(); mock.attach(ctx); errs = []
    url = BASE + ("&debug=1" if QUICK else "")
    p = new_page(ctx, errs, url)
    consent(p, "LSTRESS1"); lr_check(p); volume(p, mock); instructions_quiz(p)
    n = 0; target = 12 if QUICK else 64; t0 = time.time(); done = set()
    while True:
        where = step_until_trial_or_end(p)
        if where != "trial":
            break
        n_rec = len(state(p)["trials"])
        if n_rec == 3:
            answer_trial(p, early_check=True)
        elif n_rec == 5:
            answer_trial(p, double=True)                     # double click on "next"
            p.wait_for_timeout(500)
            ok(len(state(p)["trials"]) == 6, f"double-click stores one trial, not two (now {len(state(p)['trials'])})")
        elif n_rec == 8 and "reload" not in done:
            done.add("reload")
            p.reload(); p.wait_for_selector("#y"); p.screenshot(path=f"{SHOTS}/resume_prompt.png"); p.click("#y")
            ok(len(state(p)["trials"]) == 8, "reload mid-block: resume keeps the 8 stored trials")
            continue
        elif n_rec == (10 if QUICK else 14) and "reopen" not in done:
            done.add("reopen")
            sid = state(p)["session"]["session_id"]; p.close()
            p = new_page(ctx, errs, url); p.wait_for_selector("#y"); p.click("#y")
            ok(state(p)["session"]["session_id"] == sid and len(state(p)["trials"]) == n_rec, f"tab closed and reopened: same session, {n_rec} trials kept")
            continue
        elif n_rec == (6 if QUICK else 30):
            mock.down = True; notes.append(f"receiver down from trial {n_rec + 1}")
            answer_trial(p)
        elif n_rec == (11 if QUICK else 50):
            mock.down = False; notes.append(f"receiver back at trial {n_rec + 1}")
            p.set_viewport_size({"width": 1024, "height": 640}); p.screenshot(path=f"{SHOTS}/trial_1024x640.png")
            answer_trial(p)
            p.set_viewport_size({"width": 1440, "height": 900})
        else:
            answer_trial(p)
        n += 1
        if n == target // 2:
            mock.vol = 70                                     # someone touches the volume keys mid-session
    p.wait_for_timeout(1500)
    S = state(p); tr = S["trials"]
    p.screenshot(path=f"{SHOTS}/end.png")
    ok(where == "end", "reached the end screen")
    ok(len(tr) == target, f"{target} trials stored (got {len(tr)})")
    ok([t["index"] for t in tr] == list(range(1, target + 1)), "trial indices 1..N with no gap or repeat")
    got = [t["index"] for c in mock.posts for t in c["trials"]]
    ok(sorted(got) == list(range(1, target + 1)), f"receiver got every trial exactly once ({len(got)} rows, {len(set(got))} unique)")
    ok(mock.posts[-1]["final"] is True, "last transmission flagged final")
    ok(S["session"].get("volume_system") == 62 and S["session"].get("volume_system_end") == 70, f"Mac volume at start/end recorded ({S['session'].get('volume_system')} -> {S['session'].get('volume_system_end')})")
    notes.append(f"left/right mistakes recorded: {S['session'].get('lr_check_errors')} (random answers, so 0 is possible)")
    ok(S["session"].get("quiz_attempts") == 2, "quiz attempts = 2")
    ok("LSTRESS1" in p.inner_text(".code"), "end screen shows the participant code")
    hid = [t for t in tr if t["hidden"]]
    ok(len(hid) == 4 and sorted(t["seat"] for t in hid) == sorted("LCCR"), "4 hidden references (L, C x2, R)")
    if not QUICK:
        mins = (time.time() - t0) / 60
        notes.append(f"S1 machine run time from first trial to end: {mins:.1f} min (answers right after 5 s, so a person will take longer)")
        dur = [t["listen_s"] for t in tr]; notes.append(f"listen_s min {min(dur):.1f}, max {max(dur):.1f}")
    ok(not errs, f"S1 no page errors {errs[:3]}")
    b.close()


def s2(pw):
    print("\n== S2 a sound file is missing ==")
    b = pw.chromium.launch(channel="chrome", args=["--autoplay-policy=no-user-gesture-required"])
    ctx = b.new_context(viewport={"width": 1280, "height": 720}); mock = Mock(); mock.attach(ctx); errs = []
    broken = {"on": True}
    ctx.route("**/audio/lab/practice/practice2*", lambda r: r.fulfill(status=404, body="") if broken["on"] else r.continue_())
    p = new_page(ctx, errs, BASE + "&debug=1")
    consent(p, "LSTRESS2"); lr_check(p, False); volume(p, mock); instructions_quiz(p)
    p.wait_for_selector("#re", timeout=30000)
    msg = p.inner_text("main") if p.query_selector("main") else p.content()
    ok("404" in msg and "practice2" in msg, "error screen names the failing file and status")
    p.screenshot(path=f"{SHOTS}/load_error.png")
    broken["on"] = False; p.click("#re")
    p.wait_for_selector("#go", timeout=30000)
    ok(not p.query_selector("#re"), "retry after the file is back continues")
    ok(not errs, f"S2 no page errors {errs[:3]}")
    b.close()


def s3(pw):
    print("\n== S3 resume prompt -> start over ==")
    b = pw.chromium.launch(channel="chrome", args=["--autoplay-policy=no-user-gesture-required"])
    ctx = b.new_context(); mock = Mock(); mock.attach(ctx); errs = []
    p = new_page(ctx, errs, BASE + "&debug=1")
    consent(p, "LSTRESS3"); sid = state(p)["session"]["session_id"]
    p.reload(); p.wait_for_selector("#n"); p.click("#n")
    p.wait_for_selector("#ok")
    ok(state(p)["session"]["session_id"] != sid, "start over gives a new session id")
    ok(state(p)["session"]["pid"] == "" or not state(p)["session"].get("consent_at"), "start over asks for consent again")
    ok(not errs, f"S3 no page errors {errs[:3]}")
    b.close()


def s4(pw):
    print("\n== S4 receiver down at the end ==")
    b = pw.chromium.launch(channel="chrome", args=["--autoplay-policy=no-user-gesture-required"])
    ctx = b.new_context(accept_downloads=True); mock = Mock(); mock.attach(ctx); errs = []
    mock.down = True
    p = new_page(ctx, errs, BASE + "&debug=1")
    consent(p, "LSTRESS4"); lr_check(p, False); volume(p, mock); instructions_quiz(p)
    while step_until_trial_or_end(p) == "trial":
        answer_trial(p)
    p.wait_for_timeout(800)
    ok("warn" in (p.get_attribute("p.warn", "class") or ""), "failure message shown")
    with p.expect_download() as d:
        p.click("#dl")
    data = json.load(open(d.value.path()))
    ok(len(data["trials"]) == 12 and data["session"]["pid"] == "LSTRESS4", "download holds all 12 trials and the session")
    p.screenshot(path=f"{SHOTS}/end_fail.png")
    mock.down = False; p.click("#rs"); p.wait_for_timeout(800)          # the network comes back: "send again"
    got = [t["index"] for c in mock.posts for t in c["trials"]]
    ok(not p.query_selector("p.warn") and sorted(got) == list(range(1, 13)) and mock.posts[-1]["final"], f"send-again after the receiver is back delivers all 12 trials ({len(got)})")
    ok(not errs, f"S4 no page errors {errs[:3]}")
    b.close()


with sync_playwright() as pw:
    for f in (s2, s3, s4, s1):
        try:
            f(pw)
        except Exception as e:
            ok(False, f"{f.__name__} crashed: {e!r}"[:300])
srv.terminate()
print("\nnotes:"); [print(" -", n) for n in notes]
print("FAILED: %d" % len(fail) if fail else "stress test passed")
sys.exit(1 if fail else 0)
