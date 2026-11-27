// node tools/test_design.js : checks of the presentation order
const fs = require("fs"), path = require("path");
const D = require("../web/design.js");
const design = JSON.parse(fs.readFileSync(path.join(__dirname, "../web/design.json")));
const orders = ["LCR", "LRC", "CLR", "CRL", "RLC", "RCL"];
const REPS = { L: 1, C: 2, R: 1 };
let fail = 0; const ok = (c, m) => { if (!c) { fail++; console.log("FAIL", m); } };
const firstPos = {}, hidPos = [];
for (let seed = 1; seed <= 600; seed++) {
  const so = orders[seed % 6], st = D.buildSteps(design, so, seed, { mode: "online", repetitions: REPS });
  const tr = st.filter((s) => s.type === "trial" && !s.practice);
  ok(tr.length === 64, "64 trials (60 + 4 hidden references)");
  ok(tr.map((t) => t.index).join() === [...Array(64)].map((_, i) => i + 1).join(), "index 1..64");
  ok(tr.map((t) => t.seat).filter((s, i, a) => i === 0 || s !== a[i - 1]).join("") === so, "seats blocked in the given order");
  for (const seat of "LCR") for (let rep = 1; rep <= 2; rep++) {
    if (rep > REPS[seat]) { ok(!tr.some((t) => t.seat === seat && t.rep === rep), "no extra repetition at side seats"); continue; }
    const h = tr.filter((t) => t.seat === seat && t.rep === rep && t.hidden);
    ok(h.length === 1 && h[0].file === design.hidden[seat] && h[0].itdg === null, "one hidden reference per repetition");
    const f = tr.filter((t) => t.seat === seat && t.rep === rep && !t.hidden).map((t) => t.file);
    ok(f.length === 15 && new Set(f).size === 15, "each condition once per repetition");
    ok(f.every((x) => design.conditions.find((c) => c.file === x && c.seat === seat)), "file belongs to the seat");
  }
  const b = tr.filter((t) => t.seat === "C"); ok(b.length === 32 && b.slice(0, 16).every((t) => t.rep === 1) && b.slice(16).every((t) => t.rep === 2), "repetition 1 before 2");
  ok(JSON.stringify(st) === JSON.stringify(D.buildSteps(design, so, seed, { mode: "online", repetitions: REPS })), "same seed, same order");
  ok(st.filter((s) => s.type === "seat").length === 3 && st.filter((s) => s.type === "break").length === 2, "3 seat screens, 2 breaks");
  ok(st.filter((s) => s.practice).length === 4, "4 practice trials");
  const hp = tr.filter((t) => t.hidden).map((t) => t.n); hidPos.push(...hp);
  const k = tr[0].itdg + "/" + tr[0].lr; firstPos[k] = (firstPos[k] || 0) + 1;
}
const lab = D.buildSteps(design, "LCR", 7, { mode: "lab", repetitions: REPS }).map((s) => s.type);
ok(!lab.includes("headphones") && lab.includes("volume"), "lab mode skips the headphone screen and keeps the volume screen");
const dbg = D.buildSteps(design, "LCR", 7, { mode: "online", repetitions: REPS, trialsPerRep: 2 }).filter((s) => s.type === "trial" && !s.practice);
ok(dbg.length === 12, "debug: 2 trials per repetition");
const c = Object.values(firstPos); console.log("first-trial condition counts over 600 sessions: min", Math.min(...c), "max", Math.max(...c), "(expected about 40)");
ok(D.buildSteps(design, "LCR", 7, { mode: "online", repetitions: REPS }).findIndex((s) => s.type === "quiz") === 1 + D.buildSteps(design, "LCR", 7, { mode: "online", repetitions: REPS }).findIndex((s) => s.type === "instructions"), "quiz right after instructions");
console.log("hidden reference position within the block: min", Math.min(...hidPos), "max", Math.max(...hidPos));
console.log(fail ? fail + " checks failed" : "all checks passed");
process.exit(fail ? 1 : 0);
