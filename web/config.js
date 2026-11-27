// Settings of the experiment page. Edit here, not in app.js.
window.P2_CONFIG = {
  version: "pilot2-0.4",
  minListenS: 5,            // "next" opens after this many seconds of listening (answers can be chosen from the start)
  autoPlay: true,           // each sound starts by itself when its screen appears
  repetitions: { L: 1, C: 2, R: 1 },   // centre seat twice (retest reliability), side seats once -> 60 trials
  seatOrders: ["LCR", "LRC", "CLR", "CRL", "RLC", "RCL"],
  online: { audioBase: "audio/online", ext: "flac", endpoint: "https://script.google.com/macros/s/AKfycbyA2QLlFxH6rIjjSIFl89rZnOf2Kkgt1ZkCcAGCMq-FGih8lQt9WZvRI0fUfOQqVx1a/exec", assign: "https://script.google.com/macros/s/AKfycbyA2QLlFxH6rIjjSIFl89rZnOf2Kkgt1ZkCcAGCMq-FGih8lQt9WZvRI0fUfOQqVx1a/exec?assign=1&mode=online" },   // Google Apps Script web app (gas/Code.gs)
  lab:    { audioBase: "audio/lab", ext: "flac", endpoint: "https://script.google.com/macros/s/AKfycbyA2QLlFxH6rIjjSIFl89rZnOf2Kkgt1ZkCcAGCMq-FGih8lQt9WZvRI0fUfOQqVx1a/exec", assign: "https://script.google.com/macros/s/AKfycbyA2QLlFxH6rIjjSIFl89rZnOf2Kkgt1ZkCcAGCMq-FGih8lQt9WZvRI0fUfOQqVx1a/exec?assign=1&mode=lab" }   // face to face: HD600 set (headphone EQ on), same receiver
};
