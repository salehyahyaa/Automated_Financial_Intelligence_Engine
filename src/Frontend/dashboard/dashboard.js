/**
 * Dashboard summary from GET /dashboard/summary. Re-run after Plaid refresh via window event.
 */
(function () {
  function apiBase() {
    var b =
      window.API_BASE ||
      ((document.querySelector('meta[name="api-base"]') || {}).content || "").trim() ||
      "http://127.0.0.1:8001";
    b = String(b).replace(/\/+$/, "");
    if (!/^https?:\/\//i.test(b)) {
      b = "http://127.0.0.1:8001";
    }
    // Static site often runs on :8000; API must not hit the same port or /dashboard/summary 404s.
    try {
      var u = new URL(b);
      if (u.port === "8000" && (u.hostname === "127.0.0.1" || u.hostname === "localhost")) {
        u.port = "8001";
        b = u.toString().replace(/\/$/, "");
      }
    } catch (e) {
      b = "http://127.0.0.1:8001";
    }
    return b;
  }

  function money(n) {
    if (n == null || n === "") return "—";
    var x = Number(n);
    if (Number.isNaN(x)) return String(n);
    return x.toLocaleString(undefined, {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 2,
    });
  }

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function attrEsc(s) {
    if (s == null) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;")
      .replace(/</g, "&lt;");
  }

  function titleCaseType(s) {
    if (!s) return "";
    var t = String(s).replace(/_/g, " ");
    return t.charAt(0).toUpperCase() + t.slice(1).toLowerCase();
  }

  /** Primary label: Plaid account name + last four when available. */
  function accountDisplayTitle(a) {
    var n = (a && (a.name || "")).trim();
    var base = n || (a && a.plaid_account_id) || "Account";
    var mask = (a && a.mask != null && String(a.mask).trim()) || "";
    if (mask) return base + " ····" + mask;
    return base;
  }

  /** User-facing cash movement: invert Plaid sign (positive Plaid outflow → negative in table). */
  function txSignedCashflow(amount) {
    var x = Number(amount);
    if (Number.isNaN(x)) return null;
    return -x;
  }

  function txAmountHtml(amount) {
    var flow = txSignedCashflow(amount);
    if (flow == null) return '<td class="dash-tx-amt">—</td>';
    var cls = "dash-tx-amt";
    if (flow > 0) cls += " dash-tx-amt--in";
    else if (flow < 0) cls += " dash-tx-amt--out";
    return '<td class="' + cls + '">' + esc(money(flow)) + "</td>";
  }

  function accountCellHtml(a) {
    var title = accountDisplayTitle(a);
    var bank = (a && a.bank && String(a.bank).trim()) || "";
    var sub = bank ? '<span class="dash-account-sub">' + esc(bank) + "</span>" : "";
    return (
      '<td class="dash-account-cell"><span class="dash-account-title">' +
      esc(title) +
      "</span>" +
      sub +
      "</td>"
    );
  }

  function renderConnectionStrip(data) {
    var el = document.getElementById("dash-connection-strip");
    if (!el) return;
    if (!data.linked || !data.institution) {
      el.innerHTML = "";
      el.classList.remove("dash-connection-strip--visible");
      return;
    }
    var inst = data.institution.display_name || "Linked institution";
    var n = (data.snapshot && data.snapshot.accounts_connected) || (data.accounts || []).length || 0;
    el.innerHTML =
      '<div class="dash-connection-inner">' +
      '<span class="dash-connection-dot" aria-hidden="true"></span>' +
      '<div class="dash-connection-text">' +
      '<span class="dash-connection-label">Connected</span>' +
      '<span class="dash-connection-name">' +
      esc(inst) +
      "</span>" +
      '<span class="dash-connection-meta">' +
      esc(String(n)) +
      " account" +
      (n === 1 ? "" : "s") +
      " at this link</span>" +
      "</div></div>";
    el.classList.add("dash-connection-strip--visible");
  }

  function renderAccounts(accounts) {
    var wrap = document.getElementById("dash-accounts-wrap");
    if (!wrap) return;
    if (!accounts || !accounts.length) {
      wrap.innerHTML =
        '<p class="dash-empty">No accounts yet. Connect a bank and tap the header refresh.</p>';
      return;
    }
    var rows = accounts
      .map(function (a) {
        return (
          "<tr>" +
          accountCellHtml(a) +
          "<td>" +
          esc(titleCaseType(a.account_type || "")) +
          "</td><td class=\"dash-table-num\">" +
          money(a.current_balance) +
          "</td></tr>"
        );
      })
      .join("");
    wrap.innerHTML =
      '<table class="dash-table dash-table--accounts"><thead><tr><th>Account</th><th>Type</th><th class="dash-table-num">Balance</th></tr></thead><tbody>' +
      rows +
      "</tbody></table>";
  }

  var TX_PREVIEW_COUNT = 8;

  function txTableRowHtml(t) {
    var acc = (t.account_name || "").trim();
    var m = t.account_mask != null && String(t.account_mask).trim();
    var accCol = acc ? acc + (m ? " ····" + m : "") : "—";
    return (
      "<tr><td>" +
      esc(t.date) +
      "</td><td>" +
      esc(accCol) +
      "</td><td>" +
      esc(t.merchant_name || "—") +
      "</td><td>" +
      esc(t.category || "") +
      "</td>" +
      txAmountHtml(t.amount) +
      "</tr>"
    );
  }

  function renderTxs(txs, snapshot) {
    var wrap = document.getElementById("dash-tx-wrap");
    if (!wrap) return;
    var totalRows = (snapshot && snapshot.transaction_row_count) || 0;
    if (!txs || !txs.length) {
      var body =
        totalRows === 0
          ? "<p><strong>No transactions in the database yet.</strong> Use the circular refresh in the header to pull the latest from Plaid into your account.</p><p class=\"dash-empty-note\">After the first sync, recent debits and credits show here with the account they hit.</p>"
          : "<p>No rows returned for this view. Try a refresh.</p>";
      wrap.innerHTML =
        '<div class="dash-empty-state">' +
        '<div class="dash-empty-state-icon" aria-hidden="true">↻</div>' +
        '<div class="dash-empty-state-body">' +
        body +
        "</div></div>";
      return;
    }
    var previewN = TX_PREVIEW_COUNT;
    var primary = txs.slice(0, previewN);
    var extra = txs.length > previewN ? txs.slice(previewN) : [];
    var rowsMain = primary.map(txTableRowHtml).join("");
    var rowsExtra = extra.map(txTableRowHtml).join("");
    var extraTbody =
      extra.length > 0
        ? '<tbody id="dash-tx-tbody-extra" class="dash-tx-tbody-extra" hidden>' + rowsExtra + "</tbody>"
        : "";
    var moreBtn =
      extra.length > 0
        ? '<button type="button" class="dash-tx-show-more" id="dash-tx-show-more" aria-expanded="false">Show more <span class="dash-tx-show-more-count">(' +
          String(extra.length) +
          ")</span></button>"
        : "";
    wrap.innerHTML =
      '<table class="dash-table dash-table--tx"><thead><tr><th>Date</th><th>Account</th><th>Merchant</th><th>Category</th><th class="dash-table-num">Amount</th></tr></thead><tbody>' +
      rowsMain +
      "</tbody>" +
      extraTbody +
      "</table>" +
      moreBtn +
      '<p class="dash-tx-footnote">Amounts use cash-flow sign: positive = inflow, negative = outflow.</p>';
    var btn = document.getElementById("dash-tx-show-more");
    if (btn) {
      btn.addEventListener("click", function () {
        var tb = document.getElementById("dash-tx-tbody-extra");
        if (tb) {
          tb.hidden = false;
          tb.removeAttribute("hidden");
        }
        btn.setAttribute("aria-expanded", "true");
        btn.remove();
      });
    }
  }

  function renderStats(data) {
    var el = document.getElementById("dash-stats");
    if (!el) return;
    var snap = data.snapshot;
    if (!data.linked || !snap) {
      el.innerHTML = "";
      return;
    }
    var acctN = snap.accounts_connected != null ? snap.accounts_connected : (data.accounts || []).length;
    var instFull = data.institution && data.institution.display_name ? String(data.institution.display_name) : "";
    var instShort = instFull ? instFull.slice(0, 28) + (instFull.length > 28 ? "…" : "") : "—";
    el.innerHTML =
      '<div class="dash-stat dash-stat--wide"><div class="dash-stat-label">Institution</div><div class="dash-stat-value dash-stat-value--accent dash-stat-value--truncate" title="' +
      attrEsc(instFull) +
      '">' +
      esc(instShort) +
      '</div></div><div class="dash-stat"><div class="dash-stat-label">Accounts connected</div><div class="dash-stat-value">' +
      String(acctN) +
      '</div></div><div class="dash-stat"><div class="dash-stat-label">Est. liquid</div><div class="dash-stat-value dash-stat-value--accent">' +
      money(snap.total_liquid_estimate) +
      '</div></div><div class="dash-stat"><div class="dash-stat-label">Net (90d)</div><div class="dash-stat-value dash-stat-value--good">' +
      money(snap.net_90d) +
      '</div></div><div class="dash-stat"><div class="dash-stat-label">Income (90d)</div><div class="dash-stat-value">' +
      money(snap.income_90d) +
      '</div></div><div class="dash-stat"><div class="dash-stat-label">Spend (90d)</div><div class="dash-stat-value">' +
      money(snap.expenses_90d) +
      '</div></div><div class="dash-stat"><div class="dash-stat-label">Transaction rows</div><div class="dash-stat-value">' +
      String(snap.transaction_row_count || 0) +
      "</div></div>";
  }

  function fetchApi(url, opts) {
    var fn = window.serverFetch || fetch;
    return fn(url, opts || {});
  }

  function loadDashboard() {
    var base = apiBase();
    var loading = document.getElementById("dash-loading");
    var content = document.getElementById("dash-content");
    var hint = document.getElementById("dash-hint");
    var sub = document.getElementById("dash-subtitle");
    if (loading) {
      loading.textContent = "Loading your snapshot…";
      loading.classList.remove("dash-content--hidden");
    }
    if (content) content.classList.add("dash-content--hidden");
    fetchApi(base + "/dashboard/summary")
      .then(function (r) {
        return r.json().then(
          function (data) {
            if (!r.ok) {
              var msg = (data && (data.detail || data.message)) || "HTTP " + r.status;
              if (r.status === 401) {
                var d401 = (data && (data.detail || data.message)) || "";
                if (typeof console !== "undefined" && console.warn) {
                  console.warn("[FinancialEngine dashboard] GET /dashboard/summary 401", data);
                }
                if (d401) {
                  msg = d401;
                  if (/Invalid or expired|signature|algorithm|JWT|decode/i.test(String(d401))) {
                    msg +=
                      " — Token rejected by API: set SUPABASE_JWT_SECRET to the Supabase Legacy JWT secret (HS256), or remove it for local no-auth.";
                  }
                } else {
                  msg =
                    "Sign in required — use Sign in on this page, or remove SUPABASE_JWT_SECRET from the API .env for local no-auth.";
                }
              }
              if (r.status === 404) {
                msg +=
                  " — is the FastAPI app restarted? This path must hit the API (default port 8001), not the static server on 8000.";
              }
              throw new Error(msg);
            }
            return data;
          },
          function () {
            throw new Error(
              "Bad response from " +
                base +
                "/dashboard/summary (HTTP " +
                r.status +
                "). Use port 8001 for the API."
            );
          }
        );
      })
      .then(function (data) {
        if (loading) loading.classList.add("dash-content--hidden");
        if (content) content.classList.remove("dash-content--hidden");
        if (!data.database_configured) {
          if (sub) sub.textContent = "Database not configured — set DATABASE_URL in repo-root .env.";
          if (hint) hint.textContent = "";
          renderConnectionStrip({ linked: false });
          renderStats({ linked: false, snapshot: null });
          renderAccounts([]);
          renderTxs([], null);
          return;
        }
        if (!data.linked) {
          if (sub) sub.textContent = "Link a bank to see balances, cash flow, and recent activity.";
          if (hint) hint.textContent = "Tip: Connect bank account in the chat menu, then use the header refresh.";
          renderConnectionStrip({ linked: false });
          renderStats({ linked: false, snapshot: null });
          renderAccounts([]);
          renderTxs([], null);
          return;
        }
        if (sub)
          sub.textContent =
            "Balances, 90-day cash-flow summary, and the latest transactions stored for your link.";
        if (hint) hint.textContent = "Header refresh syncs Plaid → database → this view.";
        renderConnectionStrip(data);
        renderStats(data);
        renderAccounts(data.accounts);
        renderTxs(data.recent_transactions, data.snapshot);
      })
      .catch(function (e) {
        if (loading) {
          loading.classList.remove("dash-content--hidden");
          loading.textContent = "Could not load dashboard: " + (e.message || String(e));
        }
      });
  }

  function fetchBearerRequired(base) {
    return fetch(base + "/config/auth-public")
      .then(function (r) {
        if (!r.ok) return { bearer_required: false };
        return r.json();
      })
      .catch(function () {
        return { bearer_required: false };
      });
  }

  function bootDashboard() {
    var base = apiBase();
    fetchBearerRequired(base).then(function (cfg) {
      if (!cfg.bearer_required) {
        loadDashboard();
        return;
      }
      window.authReady.then(function () {
        if (!window.supabaseAuth) {
          var loading = document.getElementById("dash-loading");
          if (loading) {
            loading.textContent =
              "API requires sign-in — set SUPABASE_URL + SUPABASE_ANON_KEY in the API .env and reload.";
            loading.classList.remove("dash-content--hidden");
          }
          return;
        }
        return window.supabaseAuth.auth.getSession();
      }).then(function (res) {
        if (!res) return;
        if (res.data && res.data.session) loadDashboard();
        else {
          var loading = document.getElementById("dash-loading");
          if (loading) {
            loading.textContent = "Sign in below to load your dashboard.";
            loading.classList.remove("dash-content--hidden");
          }
        }
      });
    });
  }

  window.loadFinancialDashboard = loadDashboard;
  document.addEventListener("DOMContentLoaded", bootDashboard);
  window.addEventListener("financial-dashboard-refresh", loadDashboard);
})();
