// Presentation order. Pure functions (no DOM), so they can be tested with node (tools/test_design.js).
(function (g) {
  function rng(seed) { // mulberry32
    let a = seed >>> 0;
    return function () { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  function shuffle(arr, r) { const a = arr.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
  // steps of one session, fully determined by (design, seatOrder, seed, options)
  function buildSteps(design, seatOrder, seed, opt) {
    const r = rng(seed), repOf = (seat) => { const v = opt.repetitions; return (v && typeof v === "object" ? v[seat] : v) || 1; }, limit = opt.trialsPerRep || 0, steps = [];
    const add = (s) => steps.push(s);
    add({ type: "consent" });
    if (opt.mode === "online") add({ type: "headphones" });
    add({ type: "lrcheck" });
    if (opt.mode === "online") add({ type: "volume" });
    add({ type: "instructions" });
    add({ type: "quiz" });
    add({ type: "practiceIntro" });
    design.practice.forEach((p, i) => add({ type: "trial", practice: true, seat: p.seat, file: p.file, n: i + 1, of: design.practice.length }));
    add({ type: "practiceEnd" });
    let index = 0;
    seatOrder.split("").forEach((seat, b) => {
      const conds = design.conditions.filter((c) => c.seat === seat);
      const reps = repOf(seat);
      const perRep = limit ? Math.min(limit, conds.length) : conds.length;
      const hid = design.hidden && design.hidden[seat], perBlock = (perRep + (hid ? 1 : 0)) * reps;
      add({ type: "seat", seat, block: b + 1, count: perBlock });
      let n = 0;
      for (let rep = 1; rep <= reps; rep++) {
        let order = shuffle(conds, r).map((c) => ({ file: c.file, itdg: c.itdg, lr: c.lr, hidden: 0 }));
        if (limit) order = order.slice(0, perRep);
        if (hid) order.splice(Math.floor(r() * (order.length + 1)), 0, { file: hid, itdg: null, lr: null, hidden: 1 }); // hidden reference at a random place
        order.forEach((c) => add({ type: "trial", practice: false, seat, block: b + 1, rep, n: ++n, of: perBlock, index: ++index, file: c.file, itdg: c.itdg, lr: c.lr, hidden: c.hidden }));
      }
      if (b < seatOrder.length - 1) add({ type: "break", block: b + 1 });
    });
    add({ type: "post" });
    add({ type: "end" });
    return steps;
  }
  const api = { rng, shuffle, buildSteps };
  g.P2Design = api;
  if (typeof module !== "undefined") module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
