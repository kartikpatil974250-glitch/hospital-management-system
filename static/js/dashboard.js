/**
 * PulseCare HMS - Interactive Dashboard Charts and Metric Visualizations
 */

document.addEventListener("DOMContentLoaded", function () {
  // Real-time local clock on dashboard
  const timeDisplay = document.getElementById("liveTimeDisplay");
  if (timeDisplay) {
    function updateClock() {
      const now = new Date();
      timeDisplay.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }
    updateClock();
    setInterval(updateClock, 1000);
  }

  // Quick search table filter helper
  const tableSearch = document.getElementById("tableSearchInput");
  if (tableSearch) {
    tableSearch.addEventListener("keyup", function () {
      const filter = this.value.toLowerCase();
      const rows = document.querySelectorAll(".table tbody tr");
      rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.indexOf(filter) > -1 ? "" : "none";
      });
    });
  }
});
