/**
 * Refresh button: POST /refresh_account_data to sync accounts and transactions.
 * Uses window.API_BASE from plaid/plaid.js.
 */

(function () {
  var refreshBtn = document.getElementById("refresh-btn");
  if (!refreshBtn) return;

  refreshBtn.addEventListener("click", function () {
    var API_BASE = window.API_BASE || "http://127.0.0.1:8001";
    refreshBtn.disabled = true;
    (window.serverFetch || fetch)(API_BASE + "/refresh_account_data", { method: "POST" }) //refresh endpoint
      .then(function (res) {
        if (!res.ok) throw new Error("Refresh failed: " + res.status);
        return res.json();
      })
      .then(function (data) {
        if (data.refreshed || data["Refreshed Acc Data"]) {
          if (typeof window.loadFinancialDashboard === "function") window.loadFinancialDashboard();
          alert("Data refreshed.");
        }
        refreshBtn.disabled = false;
      })
      .catch(function (err) {
        console.error("Refresh error:", err);
        alert("Could not refresh. Make sure the backend is running (same host/port as api-base meta / PORT in .env).");
        refreshBtn.disabled = false;
      });
  });
})();
