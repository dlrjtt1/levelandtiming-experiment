"""Walk through one full session (Korean, online, real timing) and save a screenshot of every screen.
usage: python tools/tour.py <outdir>   (serves web/ itself; needs playwright and web/audio_test/{main,practice}/*.wav)"""
import json, os, subprocess, sys, time, random
FAST = len(sys.argv) > 2 and sys.argv[2] == "fast"   # debug mode: 2 trials per repetition, 1 s minimum listening
from playwright.sync_api import sync_playwright
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web")
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
srv = subprocess.Popen([sys.executable, "-m", "http.server", "8767", "--directory", root], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
shot_n = [0]
def shot(p, name, full=False):
    shot_n[0] += 1; p.wait_for_timeout(250); p.screenshot(path=os.path.join(out, f"{shot_n[0]:02d}_{name}.png"), full_page=full)
with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", args=["--autoplay-policy=no-user-gesture-required"]); p = b.new_page(viewport={"width": 1440, "height": 900})
    errs = []; p.on("pageerror", lambda e: errs.append(str(e)))
    # pretend a results server exists so the end screen shows the normal message
    p.route("**/config.js", lambda r: r.fulfill(content_type="text/javascript", body=open(os.path.join(root, "config.js")).read().replace('endpoint: "", assign: ""', 'endpoint: "/api/results", assign: ""')))
    p.route("**/api/results", lambda r: r.fulfill(json={"ok": True}))
    p.goto("http://localhost:8767/?mode=online&audiobase=audio_test&ext=wav&order=CLR" + ("&debug=1" if FAST else ""))
    click = lambda s: p.click(s, timeout=60000)
    p.wait_for_selector("[data-l]"); shot(p, "language"); click("[data-l=ko]")
    p.wait_for_selector("#ok"); shot(p, "consent", True); p.check("#ok"); click("#go")
    p.wait_for_selector("#hp"); p.fill("#hp", "Sennheiser HD600"); p.check("#ok"); shot(p, "headphones", True); click("#go")
    p.wait_for_selector("#bl"); shot(p, "lr_check")
    while not p.query_selector("#go"):
        click("#pl"); p.wait_for_timeout(100); click(random.choice(["#bl", "#br"])); p.wait_for_timeout(50)
    shot(p, "lr_check_done"); click("#go")
    p.wait_for_selector("#pl"); shot(p, "volume", True); click("#pl"); p.wait_for_timeout(3300); click("#go")
    p.wait_for_selector("table.grid"); shot(p, "instructions", True); click("#go")
    p.wait_for_selector(".quiz"); shot(p, "quiz", True)
    p.check("input[name=qz1][value='b']"); p.check("input[name=qz2][value='b']"); p.check("input[name=qz3][value='a']"); click("#go"); shot(p, "quiz_one_wrong", True)
    p.check("input[name=qz1][value='a']"); click("#go")
    p.wait_for_selector("#go"); shot(p, "practice_intro"); click("#go")
    seen = set(); n = 0
    while True:
        p.wait_for_selector("#go, #dl", timeout=60000)
        if p.query_selector("#dl"): shot(p, "end"); break
        st = p.evaluate("(() => { const s = window.__p2.state(); return window.__p2.steps()[s.idx]; })()")
        ty = st["type"]; key = ty + ("_practice" if st.get("practice") else "") + ("_" + st["seat"] if ty == "seat" else "")
        if ty == "trial":
            if key not in seen: shot(p, key + "_before_listening")
            p.wait_for_selector("input[name=q1]:not([disabled])", timeout=8000); p.wait_for_timeout(1300 if FAST else 5300)
            for q in ("q1", "q2", "q3"): p.click(f"label:has(input[name={q}][value='{random.randint(1, 5)}'])")
            if key not in seen: shot(p, key + "_answered"); seen.add(key)
            n += 1; click("#go")
        elif ty == "seat":
            if key not in seen: shot(p, key); seen.add(key)
            click("#pl"); p.wait_for_selector("#go:not([disabled])", timeout=60000); click("#go")
        elif ty == "post":
            p.click("label:has(input[name=p1][value='2'])"); p.click("label:has(input[name=p3][value='3'])"); p.check("input[name=p2][value='a']"); p.fill("#p4", "5"); p.check("input[name=p5][value='no']")
            shot(p, "post", True); click("#go")
        else:
            if key not in seen: shot(p, key); seen.add(key)
            click("#go")
    S = p.evaluate("window.__p2.state()")
    print("recorded trials", len(S["trials"]), "hidden", sum(t["hidden"] for t in S["trials"]), "errors", errs)
    b.close()
srv.terminate()
