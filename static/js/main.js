// static/js/main.js
// Drives the conic-gradient fill on .overall-score-ring from its
// data-score attribute, and auto-dismisses flash alerts.

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".overall-score-ring[data-score]").forEach((el) => {
    const score = parseFloat(el.getAttribute("data-score")) || 0;
    el.style.setProperty("--score", Math.max(0, Math.min(100, score)));
  });

  document.querySelectorAll(".alert").forEach((alertEl) => {
    setTimeout(() => {
      const alert = bootstrap.Alert.getOrCreateInstance(alertEl);
      alert.close();
    }, 8000);
  });
});
