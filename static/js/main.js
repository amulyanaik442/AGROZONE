// AgroZone — minimal JS helpers
// GPS tab is default; state tab hides lat/lon inputs to avoid validation conflict

document.addEventListener("DOMContentLoaded", () => {
  // Animate score bars on result page
  document.querySelectorAll(".bar-fill").forEach(bar => {
    const w = bar.style.width;
    bar.style.width = "0";
    setTimeout(() => { bar.style.width = w; }, 100);
  });
});
