/* ============================================================
   Stream Overlay — script.js
   ============================================================ */

const $ = (id) => document.getElementById(id);

/* ---------- Now Playing: override via URL, e.g. ?game=Smite%202 ---------- */
const params = new URLSearchParams(location.search);
const game = params.get("game");
if (game) {
  $("game-name").textContent = game;
}

/* ---------- Alert system ---------- */
let alertTimer = null;

function showAlert(title, message) {
  $("alert-title").textContent = title;
  $("alert-message").textContent = message;
  const alertEl = $("alert");

  // Restart the CSS animation so rapid alerts still animate.
  alertEl.classList.remove("show");
  void alertEl.offsetWidth; // force reflow
  alertEl.classList.add("show");

  clearTimeout(alertTimer);
  alertTimer = setTimeout(() => alertEl.classList.remove("show"), 5000);
}

// Expose globally so external widgets can trigger it:
//   window.postMessage({ title: "New Sub", message: "Thanks!" }, "*");
window.showAlert = showAlert;

window.addEventListener("message", (e) => {
  const d = e.data;
  if (d && typeof d === "object" && d.title !== undefined) {
    showAlert(d.title, d.message || "");
  }
});

/* ---------- Preview: add ?test=1 to the URL to preview an alert ---------- */
if (params.get("test") === "1") {
  setTimeout(() => showAlert("New Follower", "Oathless just followed!"), 800);
}
