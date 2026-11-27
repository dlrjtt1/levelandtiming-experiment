"""One complete session of the experiment page (all 64 trials, real stimuli, real waiting times) by a simulated participant,
to test the whole flow and the data it produces and to time it.
usage: python tools/sim_run.py <pid> <seat order> <profile> <seed> <out dir> [port]
profile: fast    = answers at once and presses "next" the moment it opens (5 s) -> shortest possible session
         typical = listens to the whole stimulus, then takes a few seconds to answer (assumed, not measured on people)
         random  = like fast, answers drawn uniformly (to test the screening criteria)
Answers of fast/typical come from an assumed model (level and ITDG effects in the direction seen in pilot 1, plus a personal offset
and noise). They are test data, not predictions. Needs web/audio/online/{main,practice}/*.flac and playwright."""
import json, os, random, subprocess, sys, time
from playwright.sync_api import sync_playwright
pid, order, profile, seed, out = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
port = int(sys.argv[6]) if len(sys.argv) > 6 else 8800 + seed
rng = random.Random(seed); os.makedirs(out, exist_ok=True)
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web")
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--directory", root], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
offset = rng.gauss(0, 0.5)
def answer(st):
    if profile == "random": return [rng.randint(1, 5) for _ in range(3)]
    if st.get("hidden") or st.get("lr") is None: mu = [4.6, 4.6, 4.5]                  # reference-like sound
    else:
        lv = {-9: 0.0, -6: -0.2, -3: -0.6, 0: -1.1, 6: -1.8}[st["lr"]]; it = {0: 0.0, 20: 0.0, 40: -0.4}[st["itdg"]]
        side = -0.3 if st["seat"] != "C" else 0.0
        mu = [4.4 + lv + it + side, 4.4 + 1.1 * lv + 1.3 * it, 4.3 + 0.8 * lv + it + 0.5 * side]
    return [min(5, max(1, round(m + offset + rng.gauss(0, 0.8)))) for m in mu]
T0 = time.time(); log = []; errs = []
def mark(kind): log.append((round(time.time() - T0, 2), kind))
with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", args=["--autoplay-policy=no-user-gesture-required", "--disable-dev-shm-usage"]); ctx = b.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True); p = ctx.new_page()
    p.on("pageerror", lambda e: errs.append(str(e)))
    p.goto(f"http://localhost:{port}/?mode=online&lang=ko&order={order}")
    click = lambda s: p.click(s, timeout=60000)
    cur = lambda: p.evaluate("(() => { const s = window.__p2.steps()[window.__p2.state().idx]; return s; })()")
    p.wait_for_selector("#ok"); mark("consent"); p.check("#ok"); p.fill("#pid", pid); click("#go")
    p.wait_for_selector("#hp"); mark("headphones"); p.fill("#hp", "sim headphones"); p.check("#ok"); click("#go")
    p.wait_for_selector("#bl"); mark("lrcheck")
    for _ in range(60):
        if p.query_selector("#go"): break
        click("#pl"); p.wait_for_timeout(1200 if profile == "typical" else 50); click(rng.choice(["#bl", "#br"])); p.wait_for_timeout(60)
    click("#go")
    p.wait_for_selector("#pl"); mark("volume"); click("#pl"); p.wait_for_timeout(10700 if profile == "typical" else 600); click("#go")
    p.wait_for_selector("table.grid"); mark("instructions"); click("#go")
    p.wait_for_selector(".quiz"); mark("quiz"); p.check("input[name=qz1][value='a']"); p.check("input[name=qz2][value='b']"); p.check("input[name=qz3][value='a']"); click("#go")
    p.wait_for_selector("#go"); mark("practiceIntro"); click("#go")
    n = 0
    while True:
        p.wait_for_selector("#go, #dl, #pl", timeout=60000)
        if p.query_selector("#dl"): break
        st = cur(); kind = st["type"]
        if kind == "trial":
            p.wait_for_selector("input[name=q1]:not([disabled])", timeout=20000); mark("practice" if st.get("practice") else "trial"); t_start = time.time()
            if profile == "typical":
                dur = 10.65 if st.get("practice") else 12.14
                p.wait_for_timeout(int(max(0, dur - (time.time() - t_start)) * 1000)); p.wait_for_timeout(int(rng.uniform(2.5, 6.0) * 1000))
            for q, v in zip(("q1", "q2", "q3"), answer(st)): p.click(f"label:has(input[name={q}][value='{v}'])")
            if rng.random() < 0.1: p.click("label.dk")
            p.wait_for_selector("#go:not([disabled])", timeout=20000); click("#go"); n += 1
        elif kind == "seat":
            mark("seat"); click("#pl"); p.wait_for_selector("#go:not([disabled])", timeout=60000); click("#go")
        elif kind == "post":
            mark("post"); p.click("label:has(input[name=p1][value='3'])"); p.click("label:has(input[name=p3][value='3'])"); p.check("input[name=p2][value='a']"); p.fill("#p4", "5"); p.check("input[name=p5][value='no']"); click("#go")
        else:
            mark(kind); click("#go")
    mark("end")
    with p.expect_download() as d: click("#dl")
    data = json.load(open(d.value.path(), encoding="utf-8")); S = p.evaluate("window.__p2.state()")
    b.close()
srv.terminate()
data["_sim"] = dict(profile=profile, seed=seed, total_s=log[-1][0], log=log, page_errors=errs, trials_in_state=len(S["trials"]))
json.dump(data, open(os.path.join(out, pid + ".json"), "w", encoding="utf-8"), ensure_ascii=False)
print(pid, order, profile, "trials", len(data["trials"]), "total %.1f min" % (log[-1][0] / 60), "errors", len(errs))
