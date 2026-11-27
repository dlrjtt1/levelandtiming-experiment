// 2nd pilot listening experiment: screens, playback, recording. Order logic is in design.js, texts in i18n/, settings in config.js.
(async function () {
  "use strict";
  const CFG = window.P2_CONFIG, Q = new URLSearchParams(location.search);
  const MODE = Q.get("mode") === "lab" ? "lab" : "online", DEBUG = Q.get("debug") === "1";
  const M = Object.assign({}, CFG[MODE]);
  if (Q.get("audiobase")) M.audioBase = Q.get("audiobase");
  if (Q.get("ext")) M.ext = Q.get("ext");
  const MIN = DEBUG ? 1 : CFG.minListenS, KEY = "levelandtiming_session_" + MODE;
  const app = document.getElementById("app");
  let T = {}, design = null, S = null, steps = [], ctx = null, cur = null;
  const buffers = new Map();

  const t = (k, v) => (T[k] || k).replace(/\{(\w+)\}/g, (_, x) => (v && v[x] != null ? v[x] : ""));
  // Seat and trial screens are drawn over a full-window picture of the hall seen from the listener's seat
  // (img/seat_{L,C,R}.jpg, rendered offline from the CR3 model, see render/); every other screen is an ordinary card.
  let bg = null;
  const seatPic = (seat) => `img/seat_${seat}.jpg`;
  // Card screens: blurred hall behind a dark card, with the stage of the session on top.
  const STAGE = { consent: 0, headphones: 0, lrcheck: 0, volume: 0, instructions: 1, quiz: 1, practiceIntro: 2, practiceEnd: 2, seat: 3, trial: 3, break: 3, post: 4, end: 4 };
  const WIDE = { instructions: 1, quiz: 1, post: 1 };
  function stageBar() {
    const st = S && steps && steps[S.idx]; if (!st || !T.stage0) return "";
    const cur = st.type === "trial" && st.practice ? 2 : STAGE[st.type];
    return `<ol class="prog">` + [0, 1, 2, 3, 4].map((k) => `<li class="${k < cur ? "done" : k === cur ? "now" : ""}">${t("stage" + k)}</li>`).join("") + `</ol>`;
  }
  const show = (html) => {
    document.body.classList.remove("immersive"); if (bg) bg.hidden = true;
    const st = S && steps && steps[S.idx];
    app.innerHTML = `${stageBar()}<div class="card${st && WIDE[st.type] ? " wide" : ""}">${html}</div>`; window.scrollTo(0, 0);
  };
  function showIn(seat, html) {
    if (!bg) { bg = document.createElement("div"); bg.id = "hallbg"; document.body.prepend(bg); }
    bg.style.backgroundImage = `url("${seatPic(seat)}")`; bg.dataset.seat = seat; bg.hidden = false;
    document.body.classList.add("immersive");
    app.innerHTML = html; window.scrollTo(0, 0);
  }
  const preloadPic = (seat) => new Promise((res) => { const im = new Image(); im.onload = im.onerror = res; im.src = seatPic(seat); });
  const $ = (s) => app.querySelector(s);
  const seatName = (s) => t("seat" + s);
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) { /* storage full or blocked: continue without resume */ } };
  const now = () => new Date().toISOString();

  // ---------- audio ----------
  function ac() {
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      try { ctx = new AC({ sampleRate: 48000 }); } catch (e) { ctx = new AC(); }
      if (S) { S.session.audio_sample_rate = ctx.sampleRate; save(); }
    }
    if (ctx.state === "suspended") ctx.resume();
    return ctx;
  }
  const url = (kind, file) => `${M.audioBase}/${kind}/${encodeURIComponent(file)}.${M.ext}`;
  function load(kind, file) {
    const k = kind + "/" + file;
    if (!buffers.has(k)) {
      const p = fetch(url(kind, file)).then((r) => { if (!r.ok) throw new Error(r.status + " " + url(kind, file)); return r.arrayBuffer(); })
        .then((b) => new Promise((res, rej) => ac().decodeAudioData(b, res, () => rej(new Error("decode " + url(kind, file))))));
      buffers.set(k, p); p.catch(() => buffers.delete(k));
    }
    return buffers.get(k);
  }
  async function preload(list) { // list of [kind, file]; shows progress, offers retry
    for (;;) {
      let done = 0;
      show(`<p>${t("loading")}</p><div class="bar"><i id="pb"></i></div>`);
      try {
        await Promise.all(list.map(([k, f]) => load(k, f).then(() => { done++; const b = $("#pb"); if (b) b.style.width = (100 * done / list.length) + "%"; })));
        return;
      } catch (e) {
        console.error(e);
        show(`<p class="warn">${t("loadError")}</p><p class="small" style="opacity:.6">${String(e && e.message || e).replace(/[<>&]/g, "")}</p><div class="row"><button id="re">${t("retry")}</button></div>`);
        await new Promise((r) => { $("#re").onclick = r; });
      }
    }
  }
  function stop() { if (cur) { const o = cur; cur = null; o.src.onended = null; try { o.src.stop(); } catch (e) { /* already stopped */ } if (o.onstop) o.onstop(); } }
  function play(buf, opt) {
    stop();
    const c = ac(), src = c.createBufferSource(), o = { src, onstop: opt && opt.onstop };
    src.buffer = buf; src.loop = !!(opt && opt.loop); src.connect(c.destination);
    src.onended = () => { if (cur === o) { cur = null; if (o.onstop) o.onstop(true); } };
    src.start(); cur = o; return o;
  }

  // ---------- small UI parts ----------
  // 5-point scale (1 = lowest, 5 = highest): words only at the two ends
  function scale(name, lo, hi) {
    return `<div class="scale" data-name="${name}"><span class="end lo">${lo}</span><div class="dots">` + [1, 2, 3, 4, 5].map((v) =>
      `<label><input type="radio" name="${name}" value="${v}"><span>${v}</span></label>`).join("") + `</div><span class="end hi">${hi}</span></div>`;
  }
  // "질문 1. 방향: 질문문" -> small label + question
  function qtext(s) {
    const m = s.match(/^(.*?)[:：]\s*(.+)$/);
    return m ? `<div class="t"><small>${m[1]}</small>${m[2]}</div>` : `<div class="t">${s}</div>`;
  }
  function bindScales(root, onchange) {
    root.querySelectorAll(".scale input").forEach((el) => el.addEventListener("change", () => {
      el.closest(".scale").querySelectorAll("label").forEach((l) => l.classList.toggle("on", l.contains(el) && el.checked));
      onchange();
    }));
  }
  const val = (name) => { const e = app.querySelector(`input[name="${name}"]:checked`); return e ? Number(e.value) || e.value : null; };
  function planSVG(seat) { // schematic plan: stage at the top, left/right as seen from the audience
    const X = (y) => 110 + y * 13, Y = (x) => 22 + (x + 9) * 12, seats = { L: -4, C: 0, R: 4 };
    let s = `<svg viewBox="0 0 220 262" xmlns="http://www.w3.org/2000/svg" font-family="sans-serif" font-size="10">`;
    s += `<rect x="${X(-7.5)}" y="${Y(-9)}" width="${15 * 13}" height="${18.5 * 12}" fill="#fafbfc" stroke="#9aa0a8"/>`;
    s += `<rect x="${X(-5.5)}" y="${Y(-9)}" width="${11 * 13}" height="${6.8 * 12}" fill="#e9edf5" stroke="#9aa0a8"/><text x="${X(0)}" y="${Y(-8)}" text-anchor="middle" fill="#6b6f76">${t("stage")}</text>`;
    s += `<line x1="${X(seats[seat])}" y1="${Y(7.84)}" x2="${X(0)}" y2="${Y(-4)}" stroke="#1f4fbf" stroke-dasharray="4 3"/>`;
    for (const y of [-5, 5]) s += `<rect x="${X(y) - 5}" y="${Y(-2) - 5}" width="10" height="10" fill="#e67e22" stroke="#333"/>`;
    s += `<text x="${X(-5)}" y="${Y(-2) + 18}" text-anchor="middle" fill="#a04000">${t("speaker")}</text>`;
    s += `<circle cx="${X(0)}" cy="${Y(-4)}" r="6" fill="#1f4fbf" stroke="#333"/><text x="${X(0) + 10}" y="${Y(-4) + 4}" fill="#1f4fbf">${t("singer")}</text>`;
    for (const k of "LCR") s += `<circle cx="${X(seats[k])}" cy="${Y(7.84)}" r="${k === seat ? 7 : 5}" fill="${k === seat ? "#1d1d1f" : "#fff"}" stroke="#333"/>`;
    s += `<text x="${X(seats[seat])}" y="${Y(7.84) + 20}" text-anchor="middle">${t("you")}</text></svg>`;
    return s;
  }

  // ---------- sending ----------
  async function send(final) {
    if (!M.endpoint) return false;
    const body = JSON.stringify({ session: S.session, trials: S.trials.slice(S.sent), first_index: S.sent + 1, final: !!final });
    try {
      // text/plain keeps the request "simple" (no preflight), which a Google Apps Script web app needs
      const r = await fetch(M.endpoint, { method: "POST", headers: { "Content-Type": "text/plain;charset=utf-8" }, body });
      if (!r.ok) throw new Error(r.status);
      S.sent = S.trials.length; save(); return true;
    } catch (e) { console.error("send failed", e); return false; }
  }
  function download() {
    const blob = new Blob([JSON.stringify({ session: S.session, trials: S.trials }, null, 1)], { type: "application/json" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = `levelandtiming_${S.session.pid}_${S.session.session_id}.json`; a.click();
  }

  // ---------- screens ----------
  const next = () => { stop(); S.idx++; save(); run(); };
  const screens = {
    consent() {
      const pid = S.session.pid || Q.get("pid") || (MODE === "online" ? "W" : "L") + S.session.session_id.slice(0, 6).toUpperCase();   // W = online, L = lab; can be overwritten
      show(`<h1>${t("introH")}</h1>${t("intro")}${t("consent")}
        <label class="check"><input type="checkbox" id="ok"><span>${t("consentCheck")}</span></label>
        <p><label>${t("pid")}<br><input type="text" id="pid" value="${pid}" maxlength="40"></label></p>
        <div class="row"><button id="go" disabled>${t("next")}</button></div><p class="credits">${t("credits")}</p>`);
      const upd = () => { $("#go").disabled = !($("#ok").checked && $("#pid").value.trim()); };
      $("#ok").onchange = upd; $("#pid").oninput = upd;
      $("#go").onclick = () => { S.session.pid = $("#pid").value.trim(); S.session.consent_at = now(); next(); };
    },
    headphones() {
      show(`<h1>${t("hpH")}</h1>${t("hp")}<p><label>${t("hpModel")}<br><input type="text" id="hp" maxlength="80"></label></p>
        <label class="check"><input type="checkbox" id="ok"><span>${t("hpCheck")}</span></label>
        <div class="row"><button id="go" disabled>${t("next")}</button></div>`);
      const upd = () => { $("#go").disabled = !($("#ok").checked && $("#hp").value.trim()); };
      $("#ok").onchange = upd; $("#hp").oninput = upd;
      $("#go").onclick = () => { S.session.headphone = $("#hp").value.trim(); next(); };
    },
    lrcheck() {
      let seq, i;
      const begin = (msg) => {
        seq = Math.random() < 0.5 ? ["L", "R"] : ["R", "L"]; i = 0;
        show(`<h1>${t("lrH")}</h1><p>${t("lr")}</p>${msg ? `<p class="warn">${msg}</p>` : ""}
          <div class="lr"><button id="pl" class="playbig" aria-label="${t("play")}"><svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg></button>
          <div class="row"><button class="ghost" id="bl" disabled>${t("left")}</button><button class="ghost" id="br" disabled>${t("right")}</button></div><p class="note" id="st">0 / 2</p></div>`);
        $("#pl").onclick = () => { beep(seq[i]); $("#bl").disabled = $("#br").disabled = false; };
        const ans = (a) => {
          if (a !== seq[i]) { S.session.lr_check_errors = (S.session.lr_check_errors || 0) + 1; save(); return begin(t("lrWrong")); }
          i++; $("#bl").disabled = $("#br").disabled = true; $("#st").textContent = `${i} / 2`;
          if (i === 2) show(`<h1>${t("lrH")}</h1><p>${t("lrOk")}</p><div class="row"><button id="go">${t("next")}</button></div>`), ($("#go").onclick = next);
        };
        $("#bl").onclick = () => ans("L"); $("#br").onclick = () => ans("R");
      };
      const beep = (side) => { // three short tones in one ear
        const c = ac(), m = c.createChannelMerger(2), g = c.createGain(), o = c.createOscillator();
        o.frequency.value = 500; g.gain.value = 0; o.connect(g); g.connect(m, 0, side === "L" ? 0 : 1); m.connect(c.destination);
        const t0 = c.currentTime + 0.05;
        for (let k = 0; k < 3; k++) { g.gain.setValueAtTime(0, t0 + k * 0.4); g.gain.linearRampToValueAtTime(0.1, t0 + k * 0.4 + 0.02); g.gain.setValueAtTime(0.1, t0 + k * 0.4 + 0.22); g.gain.linearRampToValueAtTime(0, t0 + k * 0.4 + 0.25); }
        o.start(t0); o.stop(t0 + 1.3);
      };
      begin("");
    },
    async volume() {
      await preload([["practice", design.volume]]);
      const buf = await load("practice", design.volume);
      show(`<h1>${t("volH")}</h1>${t("vol")}<div class="row"><button id="pl">${t("play")}</button><button id="go" disabled>${t("volDone")}</button></div>`);
      let t0 = 0, heard = 0;
      $("#pl").onclick = () => {
        if (cur) { stop(); return; }
        t0 = performance.now(); $("#pl").textContent = t("stop");
        play(buf, { loop: true, onstop: () => { heard += (performance.now() - t0) / 1000; const b = $("#pl"); if (b) b.textContent = t("play"); } });
        setTimeout(() => { const b = $("#go"); if (b) b.disabled = false; }, DEBUG ? 300 : 3000);
      };
      $("#go").onclick = () => { stop(); S.session.volume_listen_s = Math.round(heard * 10) / 10; next(); };
    },
    instructions() { show(`<h1>${t("insH")}</h1>${t("ins")}<div class="row"><button id="go">${t("next")}</button></div>`); $("#go").onclick = next; },
    quiz() {
      // comprehension check on the meaning of the questions (no sound). Wrong answers show the explanation; retry until all correct.
      const items = [["qz1", "a"], ["qz2", "b"], ["qz3", "a"]], opts = { qz1: ["c", "a", "d", "b"], qz2: ["d", "a", "b", "c"], qz3: ["b", "a"] };
      const ch = { a: "qzHL", b: "qzLH", c: "qzHH", d: "qzLL" }; // labels for q1/q3 combinations: a = Q1 low, Q3 high ...
      show(`<h1>${t("qzH")}</h1><p>${t("qz")}</p>` + items.map(([k]) => `<div class="q quiz" id="${k}"><div class="t">${t(k)}</div>` +
        opts[k].map((o) => `<label class="check"><input type="radio" name="${k}" value="${o}"><span>${t(k === "qz3" ? "qz3" + o : ch[o])}</span></label>`).join("") +
        `<p class="why" hidden>${t(k + "why")}</p></div>`).join("") + `<div class="row"><button id="go" disabled>${t("qzCheck")}</button></div>`);
      const upd = () => { $("#go").disabled = !items.every(([k]) => val(k)); };
      app.querySelectorAll(".quiz input").forEach((e) => (e.onchange = upd));
      S.session.quiz_wrong = S.session.quiz_wrong || {};
      $("#go").onclick = () => {
        S.session.quiz_attempts = (S.session.quiz_attempts || 0) + 1;
        let allOk = true;
        items.forEach(([k, right]) => {
          const okk = val(k) === right, box = $("#" + k);
          box.classList.toggle("bad", !okk); box.classList.toggle("good", okk); box.querySelector(".why").hidden = okk;
          if (!okk) { allOk = false; S.session.quiz_wrong[k] = (S.session.quiz_wrong[k] || 0) + 1; }
        });
        save();
        if (allOk) return next();
        $("#go").textContent = t("qzRetry"); window.scrollTo(0, 0);
      };
    },
    async practiceIntro() {
      await preload(design.practice.map((p) => ["practice", p.file]));
      show(`<h1>${t("pracH")}</h1><p>${t("prac")}</p><div class="row"><button id="go">${t("start")}</button></div>`); $("#go").onclick = next;
    },
    practiceEnd() { show(`<h1>${t("pracH")}</h1><p>${t("pracEnd")}</p><div class="row"><button id="go">${t("next")}</button></div>`); $("#go").onclick = next; },
    async seat(st) {
      buffers.clear();
      const files = [["main", design.references[st.seat]]];
      for (let j = S.idx + 1; j < steps.length && steps[j].type === "trial"; j++) if (!files.some((f) => f[1] === steps[j].file)) files.push(["main", steps[j].file]);
      await preload(files); await preloadPic(st.seat);
      const ref = await load("main", design.references[st.seat]);
      showIn(st.seat, `<div class="panel">
        <h1>${t("seatH", { seat: seatName(st.seat) })}</h1><p>${t("seatView")}</p>
        <p>${t("seatRef")}</p><p>${t("seatCount", { count: st.count })}</p>
        <div class="row"><button id="pl">${t("refPlay")}</button><button id="go" disabled>${t("next")}</button></div></div>`);
      $("#pl").onclick = () => {
        $("#pl").disabled = true; $("#pl").textContent = t("refPlaying");
        play(ref, { onstop: () => { const b = $("#go"); if (b) b.disabled = false; S.session["ref_played_" + st.seat] = (S.session["ref_played_" + st.seat] || 0) + 1; save(); } });
      };
      $("#go").onclick = next;
    },
    async trial(st) {
      const kind = st.practice ? "practice" : "main";
      let buf;
      try { buf = await load(kind, st.file); } catch (e) { await preload([[kind, st.file]]); buf = await load(kind, st.file); }
      const tag = st.practice ? t("practiceTag", { n: st.n, of: st.of, seat: seatName(st.seat) }) : t("progress", { seat: seatName(st.seat), n: st.n, of: st.of });
      showIn(st.seat, `<div class="panel trialpanel">
        <div class="head"><span class="tag">${tag}</span><button id="pl">${t("play")}</button><div class="bar"><i id="pb"></i></div><button id="go" disabled>${t("next")}</button></div>
        <p class="note">${t("trialHint", { s: CFG.minListenS })}</p>
        <div id="qs" class="locked">
          <div class="q">${qtext(t("q1"))}<div class="withdk">${scale("q1", t("q1a"), t("q1b"))}<label class="dk"><input type="checkbox" id="q1dk"><span>${t("q1dk")}</span></label></div></div>
          <div class="q">${qtext(t("q2"))}${scale("q2", t("q2a"), t("q2b"))}</div>
          <div class="q">${qtext(t("q3"))}${scale("q3", t("q3a"), t("q3b"))}</div>
        </div></div>`);
      const inputs = app.querySelectorAll("#qs input"); inputs.forEach((e) => (e.disabled = true));
      const goLabel = t("next");
      let plays = 0, heard = 0, t0 = null, tFirst = null, unlocked = false, timer = null;
      const listened = () => heard + (t0 != null ? Math.min((performance.now() - t0) / 1000, buf.duration) : 0);
      const tick = () => {
        const pb = $("#pb"); if (!pb) return clearInterval(timer);
        pb.style.width = (t0 != null ? Math.min(100, 100 * (performance.now() - t0) / 1000 / buf.duration) : 0) + "%";
        // answers can be chosen as soon as the sound starts; "next" opens after MIN seconds of listening (count-down on the button)
        const left = MIN - listened();
        if (!unlocked && left <= 0) { unlocked = true; gate(); }
        const g = $("#go"); if (g) g.textContent = unlocked || tFirst == null ? goLabel : `${goLabel} · ${Math.ceil(left)}`;
      };
      const gate = () => { const g = $("#go"); if (g) g.disabled = !(unlocked && val("q1") && val("q2") && val("q3")); };
      timer = setInterval(tick, 50);
      const start = () => {
        plays++; t0 = performance.now(); if (tFirst == null) { tFirst = t0; $("#qs").classList.remove("locked"); inputs.forEach((e) => (e.disabled = false)); }
        $("#pl").textContent = t("stop");
        play(buf, { onstop: () => { heard = listened(); t0 = null; const b = $("#pl"); if (b) b.textContent = t("replay"); } });
      };
      $("#pl").onclick = () => { if (cur) { stop(); return; } start(); };
      bindScales(app, gate);
      // the sound starts by itself (one click less per sound) when the browser allows it; otherwise the play button is used
      if (CFG.autoPlay && ac().state === "running") setTimeout(() => { if ($("#pl") && tFirst == null && !cur) start(); }, 350);
      $("#go").onclick = () => {
        const rec = { q1: val("q1"), q1_hard: $("#q1dk").checked ? 1 : 0, q2: val("q2"), q3: val("q3") };
        stop(); clearInterval(timer);
        if (!st.practice) {
          S.trials.push({ session_id: S.session.session_id, index: st.index, block: st.block, seat: st.seat, rep: st.rep, n: st.n, file: st.file, hidden: st.hidden, itdg_ms: st.itdg, level_ratio_db: st.lr,
            q1: rec.q1, q1_hard: rec.q1_hard, q2: rec.q2, q3: rec.q3, plays, listen_s: Math.round(heard * 100) / 100, rt_s: Math.round((performance.now() - tFirst) / 10) / 100, at: now() });
          const last = steps[S.idx + 1].type !== "trial";
          S.idx++; save();
          if (last) send(false); // end of a seat: send what we have, do not wait
          return run();
        }
        next();
      };
    },
    break_(st) {
      const seats = steps.filter((x) => x.type === "seat");
      show(`<div class="mid"><p class="eyebrow">${t("breakH")}</p><h1>${t("brkDone", { seat: seatName(seats[st.block - 1].seat) })}</h1>
        <ul class="seats">` + seats.map((x) => `<li class="${x.block <= st.block ? "done" : x.block === st.block + 1 ? "now" : ""}"><b>${seatName(x.seat)}</b><span>${
          x.block <= st.block ? `${x.count} / ${x.count}` : t(x.block === st.block + 1 ? "brkNextN" : "brkN", { count: x.count })}</span></li>`).join("") + `</ul>
        <p>${t("brk")}</p><div class="row"><button id="go">${t("brkNext")}</button></div></div>`);
      $("#go").onclick = next;
    },
    post() {
      show(`<h1>${t("postH")}</h1>
        <div class="q"><div class="t">${t("p1")}</div>${scale("p1", t("pLo"), t("pHi"))}</div>
        <div class="q"><div class="t">${t("p2")}</div>${["a", "b", "c", "d"].map((k) => `<label class="check"><input type="checkbox" name="p2" value="${k}"><span>${t("p2" + k)}</span></label>`).join("")}<input type="text" id="p2o" maxlength="200"></div>
        <div class="q"><div class="t">${t("p3")}</div>${scale("p3", t("pLo"), t("pHi"))}</div>
        <div class="q"><div class="t">${t("p4")}</div><input type="number" id="p4" min="0" max="80" step="1" style="max-width:120px"></div>
        <div class="q"><div class="t">${t("p5")}</div>${["yes", "no", "dk"].map((k) => `<label class="check"><input type="radio" name="p5" value="${k}"><span>${t(k)}</span></label>`).join("")}</div>
        <div class="q"><div class="t">${t("p6")}</div><textarea id="p6" maxlength="2000"></textarea></div>
        <div class="row"><button id="go" disabled>${t("submit")}</button></div>`);
      const upd = () => { $("#go").disabled = !(val("p1") && val("p3") && val("p5")); };
      bindScales(app, upd); app.querySelectorAll('input[name="p5"]').forEach((e) => (e.onchange = upd));
      $("#go").onclick = () => {
        S.session.post = { q1q3_difficult: val("p1"), unstable_how: [...app.querySelectorAll('input[name="p2"]:checked')].map((e) => e.value).join(""), unstable_other: $("#p2o").value.trim(),
          fatigue: val("p3"), experience_years: $("#p4").value === "" ? null : Number($("#p4").value), hearing_problem: val("p5"), comments: $("#p6").value.trim() };
        S.session.finished_at = now(); next();
      };
    },
    async end() {
      window.onbeforeunload = null;
      show(`<h1>${t("endH")}</h1><p>${t("sending")}</p>`);
      const ok = await send(true);
      S.done = true; save();
      show(`<h1>${t("endH")}</h1><p class="${ok ? "" : "warn"}">${t(ok ? "endOk" : "endFail")}</p><div class="row"><button class="${ok ? "ghost" : ""}" id="dl">${t("download")}</button></div>`);
      $("#dl").onclick = download;
    }
  };
  function run() {
    const st = steps[S.idx];
    if (DEBUG) console.log("step", S.idx, st);
    (screens[st.type === "break" ? "break_" : st.type])(st);
  }

  // ---------- start ----------
  async function setLang(lang) { T = await (await fetch(`i18n/${lang}.json`)).json(); document.documentElement.lang = lang; document.title = t("title"); }
  const build = () => window.P2Design.buildSteps(design, S.session.seat_order, S.session.seed, { mode: MODE, repetitions: CFG.repetitions, trialsPerRep: DEBUG ? 2 : 0 });
  async function assignOrder() {
    const o = Q.get("order"); if (o && CFG.seatOrders.includes(o)) return [o, "url"];
    if (M.assign && !DEBUG) { try { const x = await (await fetch(M.assign, { cache: "no-store" })).json(); if (CFG.seatOrders.includes(x.order)) return [x.order, "server"]; } catch (e) { /* fall through */ } }
    return [CFG.seatOrders[Math.floor(Math.random() * CFG.seatOrders.length)], "random"];
  }
  async function fresh(lang) {
    await setLang(lang);
    const rnd = new Uint32Array(3); crypto.getRandomValues(rnd);
    const [order, src] = await assignOrder();
    S = { idx: 0, sent: 0, done: false, trials: [], session: { session_id: rnd[1].toString(16).padStart(8, "0") + rnd[2].toString(16).padStart(8, "0"), pid: "", mode: MODE, lang, version: CFG.version, debug: DEBUG,
      seat_order: order, seat_order_source: src, seed: rnd[0], min_listen_s: MIN, auto_play: !!CFG.autoPlay, stimulus_set: design.stimulus_set.brir_sofa_sha256.slice(0, 12), audio_ext: M.ext,
      user_agent: navigator.userAgent, screen: `${screen.width}x${screen.height}`, started_at: now() } };
    steps = build(); save(); go();
  }
  function go() { window.onbeforeunload = (e) => { e.preventDefault(); e.returnValue = ""; }; run(); }
  window.__p2 = { state: () => S, steps: () => steps };

  design = await (await fetch("design.json")).json();
  let saved = null; try { saved = JSON.parse(localStorage.getItem(KEY)); } catch (e) { saved = null; }
  if (saved && !saved.done && saved.session && saved.session.debug === DEBUG && saved.session.version === CFG.version) {
    await setLang(saved.session.lang);
    show(`<p>${t("resumeQ")}</p><div class="row"><button id="y">${t("resumeYes")}</button><button class="ghost" id="n">${t("resumeNo")}</button></div>`);
    $("#y").onclick = () => { S = saved; steps = build(); go(); };
    $("#n").onclick = () => { localStorage.removeItem(KEY); location.reload(); };
    return;
  }
  const ql = Q.get("lang");
  if (["ko", "ja", "en"].includes(ql)) return fresh(ql);
  show(`<div class="mid"><p class="eyebrow">언어 / 言語 / Language</p><div class="langs"><button class="ghost" data-l="ko">한국어</button><button class="ghost" data-l="ja">日本語</button><button class="ghost" data-l="en">English</button></div></div>`);
  app.querySelectorAll("[data-l]").forEach((b) => (b.onclick = () => fresh(b.dataset.l)));
})();
