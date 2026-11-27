// Settings of the experiment page. Edit here, not in app.js.
window.P2_CONFIG = {
  version: "pilot2-0.4",
  minListenS: 5,            // "next" opens after this many seconds of listening (answers can be chosen from the start)
  autoPlay: true,           // each sound starts by itself when its screen appears
  repetitions: { L: 1, C: 2, R: 1 },   // centre seat twice (retest reliability), side seats once -> 60 trials
  seatOrders: ["LCR", "LRC", "CLR", "CRL", "RLC", "RCL"],
  online: { audioBase: "audio/online", ext: "flac", endpoint: "", assign: "" },   // endpoint: Google Apps Script URL (to be set)
  lab:    { audioBase: "/audio",       ext: "wav",  endpoint: "/api/results", assign: "/api/assign" }  // served by the local Rust server
};
