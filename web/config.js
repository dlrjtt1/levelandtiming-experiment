// Settings of the experiment page. Edit here, not in app.js.
window.P2_CONFIG = {
  version: "pilot2-0.4",
  minListenS: 5,            // "next" opens after this many seconds of listening (answers can be chosen from the start)
  autoPlay: true,           // each sound starts by itself when its screen appears
  repetitions: { L: 1, C: 2, R: 1 },   // centre seat twice (retest reliability), side seats once -> 60 trials
  seatOrders: ["LCR", "LRC", "CLR", "CRL", "RLC", "RCL"],
  ethics: {                 // shown on the consent screen; fill in before data collection (empty = "[TBD]" on screen)
    experimenter: "",       // e.g. "柳 東均（東京藝術大学 研究生） name@example.com"
    pi: "",                 // research supervisor (研究責任者), name, title, e-mail
    deadline: "",           // last day to withdraw consent, e.g. "2027年3月31日"
    retention: "",          // how long data are kept, e.g. "論文発表後10年間"
    approval: ""            // approval number of the ethics review
  },
  online: { audioBase: "audio/online", ext: "flac", endpoint: "https://script.google.com/macros/s/AKfycbyA2QLlFxH6rIjjSIFl89rZnOf2Kkgt1ZkCcAGCMq-FGih8lQt9WZvRI0fUfOQqVx1a/exec", assign: "https://script.google.com/macros/s/AKfycbyA2QLlFxH6rIjjSIFl89rZnOf2Kkgt1ZkCcAGCMq-FGih8lQt9WZvRI0fUfOQqVx1a/exec?assign=1&mode=online" },   // Google Apps Script web app (gas/Code.gs)
  lab:    { audioBase: "audio/lab", ext: "flac", endpoint: "https://script.google.com/macros/s/AKfycbyA2QLlFxH6rIjjSIFl89rZnOf2Kkgt1ZkCcAGCMq-FGih8lQt9WZvRI0fUfOQqVx1a/exec", assign: "https://script.google.com/macros/s/AKfycbyA2QLlFxH6rIjjSIFl89rZnOf2Kkgt1ZkCcAGCMq-FGih8lQt9WZvRI0fUfOQqVx1a/exec?assign=1&mode=lab" }   // face to face: HD600 set (headphone EQ on), same receiver
};
