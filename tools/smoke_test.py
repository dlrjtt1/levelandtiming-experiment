"""End-to-end run of the page in headless Chrome (debug mode: 2 trials per repetition).
usage: python tools/smoke_test.py   (serves web/ itself; needs playwright and web/audio_test/{main,practice}/*.wav)"""
import json, os, subprocess, sys, time, random
from playwright.sync_api import sync_playwright
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web")
srv = subprocess.Popen([sys.executable, "-m", "http.server", "8765", "--directory", root], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
fail = []
def ok(c, m):
    if not c: fail.append(m); print("FAIL", m)
def run(pw, mode, lang, shots):
    b = pw.chromium.launch(channel="chrome", args=["--autoplay-policy=no-user-gesture-required"]); p = b.new_page(viewport={"width": 1440, "height": 900})
    errs = []; p.on("pageerror", lambda e: errs.append(str(e))); posted = []
    if mode == "lab":
        p.route("https://script.google.com/**", lambda r: (posted.append(json.loads(r.request.post_data)), r.fulfill(json={"ok": True, "stored": 0}, headers={"Access-Control-Allow-Origin": "*"})) if r.request.method == "POST" else r.fulfill(json={"order": "RCL"}, headers={"Access-Control-Allow-Origin": "*"}))
    p.goto(f"http://localhost:8765/?mode={mode}&debug=1&lang={lang}&audiobase=audio_test&ext=wav" + ("&order=LRC" if mode == "online" else ""))
    click = lambda s: p.click(s, timeout=20000)
    p.wait_for_selector("#ok"); p.check("#ok"); p.fill("#pid", "T01"); click("#go")
    if mode == "online":
        p.wait_for_selector("#hp"); ok(p.is_disabled("#go"), "headphone screen needs model and tick"); p.fill("#hp", "Test HD600"); p.check("#ok"); click("#go")
    # left-right check: answer wrong once, then right
    p.wait_for_selector("#bl"); click("#pl"); click("#bl"); p.wait_for_timeout(100)
    for _ in range(6):
        if p.query_selector("#go"): break
        click("#pl"); click("#bl"); p.wait_for_timeout(50)
        if p.query_selector("#go"): break
        if p.query_selector(".warn") and p.is_disabled("#bl"): continue
    # brute force until confirmed
    for _ in range(40):
        if p.query_selector("#go"): break
        click("#pl"); click(random.choice(["#bl", "#br"])); p.wait_for_timeout(30)
    click("#go")
    p.wait_for_selector("#vs"); ok(p.is_disabled("#go"), "volume: done disabled before listening"); click("#pl"); p.wait_for_timeout(600)
    if mode == "lab": ok(p.is_disabled("#go"), "lab volume: setting required"); p.fill("#vs", "knob 12 o'clock")
    click("#go")
    p.wait_for_selector("table.grid"); 
    if shots: p.screenshot(path=f"/tmp/shot_{lang}_instructions.png", full_page=True)
    click("#go")
    # comprehension check: first attempt with one wrong answer, then all right
    p.wait_for_selector(".quiz"); p.check("input[name=qz1][value='b']"); p.check("input[name=qz2][value='b']"); p.check("input[name=qz3][value='a']"); click("#go")
    p.wait_for_timeout(200); ok(p.is_visible("#qz1 .why") and not p.is_visible("#qz2 .why"), "quiz: explanation only for the wrong item")
    if shots: p.screenshot(path=f"/tmp/shot_{lang}_quiz_wrong.png", full_page=True)
    p.check("input[name=qz1][value='a']"); click("#go")
    p.wait_for_selector("#go"); click("#go")          # practice intro
    n_trials = 0
    while True:
        p.wait_for_selector("#go, #dl, #pl", timeout=30000)
        if p.query_selector("#dl"): break
        if p.query_selector("#qs"):
            p.wait_for_selector("input[name=q1]:not([disabled])", timeout=5000)      # the sound starts by itself and the scales open with it
            ok(p.inner_text("#pl") != "" and p.evaluate("window.__p2.state().session.auto_play") is True, "auto play")
            ok(p.evaluate("(() => { const b = document.getElementById('hallbg'); return document.body.classList.contains('immersive') && b && !b.hidden && b.style.backgroundImage.includes('img/seat_' + b.dataset.seat + '.jpg') && (window.__p2.steps()[window.__p2.state().idx].seat === b.dataset.seat); })()"), 'seat picture behind the panel')
            if shots and n_trials == 5: p.screenshot(path=f"/tmp/shot_{lang}_trial.png")
            if n_trials % 2: p.click("label.dk")
            for q in ("q1", "q2", "q3"):
                ok(p.is_disabled("#go"), "next disabled until all three answered"); p.click(f"label:has(input[name={q}][value='{random.randint(1,5)}'])")
            p.wait_for_selector("#go:not([disabled])", timeout=5000)                   # opens after the minimum listening time
            n_trials += 1; click("#go")
        elif p.query_selector(".panel #pl") and not p.query_selector("#qs"):
            ok(p.evaluate("(() => { const b = document.getElementById('hallbg'); return document.body.classList.contains('immersive') && b && !b.hidden && b.style.backgroundImage.includes('img/seat_' + b.dataset.seat + '.jpg') && (window.__p2.steps()[window.__p2.state().idx].seat === b.dataset.seat); })()"), 'seat picture behind the panel')
            ok(p.is_disabled("#go"), "seat: next disabled before the reference")
            if shots: p.screenshot(path=f"/tmp/shot_{lang}_seat.png")
            click("#pl"); p.wait_for_selector("#go:not([disabled])", timeout=30000); ok(p.is_disabled("#pl"), "reference cannot be replayed"); click("#go")
        elif p.query_selector("input[name=p5]"):
            p.click("label:has(input[name=p1][value='2'])"); p.click("label:has(input[name=p3][value='4'])"); p.check("input[name=p2][value='a']"); p.fill("#p4", "5"); p.check("input[name=p5][value='no']"); click("#go")
        else: click("#go")
    S = p.evaluate("window.__p2.state()"); tr = S["trials"]
    ok(n_trials == 4 + 12, f"{mode}: 4 practice + 12 recorded trials (got {n_trials})"); ok(len(tr) == 12, "12 trials stored")
    ok("".join(dict.fromkeys(t["seat"] for t in tr)) == S["session"]["seat_order"], "seat blocks follow the assigned order")
    ok(all(t["listen_s"] >= 1 and t["plays"] == 1 and 1 <= t["q1"] <= 5 and t["q1_hard"] in (0, 1) for t in tr), "trial fields filled"); ok({t["q1_hard"] for t in tr} == {0, 1}, "hard-to-judge tick stored")
    ok(all(t["file"].startswith(t["seat"] + "_itdg%d_lr" % t["itdg_ms"]) for t in tr if not t["hidden"]), "file matches seat and ITDG")
    ok(sorted(t["seat"] for t in tr if t["hidden"]) == sorted("LCCR") and all(t["file"] == t["seat"] + "_s00" for t in tr if t["hidden"]), "hidden references: L, C x2, R")
    ok(S["session"]["quiz_attempts"] == 2 and S["session"]["quiz_wrong"] == {"qz1": 1}, "quiz attempts recorded")
    ok(S["session"]["audio_sample_rate"] == 48000, "48 kHz context"); ok(S["session"]["post"]["hearing_problem"] == "no", "post answers stored")
    ok(all(S["session"].get("ref_played_" + s) == 1 for s in "LCR"), "reference played once per seat")
    if mode == "lab":
        ok(S["session"]["volume_setting"] == "knob 12 o'clock", "lab: volume setting stored")
        got = [t["index"] for c in posted for t in c["trials"]]; ok(got == list(range(1, 13)), f"lab: every trial posted exactly once ({got})"); ok(posted[-1]["final"] and len(posted) == 4, "lab: 3 block posts + final")
        ok("headphone" not in S["session"], "lab: no headphone screen")
    else:
        ok(S["session"]["seat_order"] == "LRC" and S["session"]["headphone"] == "Test HD600", "online: order from url, headphone stored")
        ok("warn" in (p.get_attribute("p.warn", "class") or ""), "online without endpoint: failure message with download")
        with p.expect_download() as d: click("#dl")
        ok(len(json.load(open(d.value.path()))["trials"]) == 12, "download holds the 12 trials")
    ok(not errs, f"no page errors {errs}"); b.close()
with sync_playwright() as pw:
    run(pw, "online", "ko", True); run(pw, "lab", "ja", True); run(pw, "online", "en", False)
srv.terminate(); print("FAILED: %d" % len(fail) if fail else "smoke test passed"); sys.exit(1 if fail else 0)
