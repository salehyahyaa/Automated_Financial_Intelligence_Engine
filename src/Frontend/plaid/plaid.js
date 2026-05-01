/**
 * Plaid Link: link token, handler, openPlaidLink for Connect bank account flow.
 * Exposes window.API_BASE and window.openPlaidLink for other scripts.
 * API base: <meta name="api-base" content="http://127.0.0.1:8001" /> in HTML, else default below (must match backend PORT).
 */
(function () {
  var meta = document.querySelector('meta[name="api-base"]');
  var fromMeta = meta && meta.getAttribute("content") && meta.getAttribute("content").trim();
  var _base = window.API_BASE || fromMeta || "http://127.0.0.1:8001";
  try {
    var _u = new URL(_base);
    if (_u.port === "8000" && (_u.hostname === "127.0.0.1" || _u.hostname === "localhost")) {
      _u.port = "8001";
    }
    window.API_BASE = _u.toString().replace(/\/+$/, "");
  } catch (e) {
    window.API_BASE = "http://127.0.0.1:8001";
  }
  var plaidHandler = null;
  var linkTokenLoadError = null;
  var linkTokenLoading = true;

  window.openPlaidLink = function () {
    if (linkTokenLoading) {
      alert("Bank link is still loading. Wait a second and try again.\n\nAPI: " + window.API_BASE);
      return;
    }
    if (linkTokenLoadError) {
      alert(linkTokenLoadError);
      return;
    }
    if (plaidHandler) plaidHandler.open();
  };

  /** Parse JSON and throw with FastAPI `detail` when status is not OK. */
  function parseApiResponse(res) {
    return res.text().then(function (text) {
      var j = {};
      try {
        j = text ? JSON.parse(text) : {};
      } catch (ignore) {
        j = {};
      }
      if (!res.ok) {
        var d = j.detail;
        var msg;
        if (typeof d === "string") {
          msg = d;
        } else if (Array.isArray(d)) {
          msg = d
            .map(function (x) {
              return (x && (x.msg || x.message)) || JSON.stringify(x);
            })
            .join("; ");
        } else {
          msg = res.statusText || "HTTP " + res.status;
        }
        var err = new Error(msg || "HTTP " + res.status);
        err.status = res.status;
        throw err;
      }
      return j;
    });
  }

  function num(v) {
    var n = Number(v);
    return isNaN(n) ? 0 : n;
  }

  function delay(ms) {
    return new Promise(function (resolve) {
      setTimeout(resolve, ms);
    });
  }

  function postLinkSyncTransactions(sf) {
    return sf(window.API_BASE + "/sync-transactions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}"
    }).then(parseApiResponse);
  }

  function postLinkRefreshAll(sf) {
    return sf(window.API_BASE + "/refresh_account_data", { method: "POST" }).then(parseApiResponse);
  }

  /**
   * First /transactions/sync right after link sometimes returns nothing; retries + same path as header refresh.
   */
  function ensureTransactionsAfterLink(sf, txResult) {
    var s0 = num(txResult && txResult.stored);
    var f0 = num(txResult && txResult.fetched);
    if (s0 > 0) {
      return Promise.resolve(txResult);
    }
    if (f0 > 0) {
      return postLinkRefreshAll(sf)
        .then(function () {
          return delay(600);
        })
        .then(function () {
          return postLinkSyncTransactions(sf);
        });
    }
    return delay(2200)
      .then(function () {
        return postLinkSyncTransactions(sf);
      })
      .then(function (tx2) {
        if (num(tx2.stored) > 0) return tx2;
        return delay(2200).then(function () {
          return postLinkSyncTransactions(sf);
        });
      })
      .then(function (tx3) {
        if (num(tx3.stored) > 0) return tx3;
        return postLinkRefreshAll(sf)
          .then(function () {
            return delay(600);
          })
          .then(function () {
            return postLinkSyncTransactions(sf);
          });
      });
  }

  function waitForSessionIfBearerRequired() {
    return fetch(window.API_BASE + "/config/auth-public")
      .then(function (r) {
        return r.ok ? r.json() : { bearer_required: false };
      })
      .catch(function () {
        return { bearer_required: false };
      })
      .then(function (cfg) {
        if (!cfg.bearer_required) return Promise.resolve();
        return window.authReady.then(function () {
          if (!window.supabaseAuth) return Promise.reject(new Error("Supabase not configured"));
          return window.supabaseAuth.auth.getSession();
        }).then(function (r) {
          if (r && r.data && r.data.session) return;
          return new Promise(function (resolve) {
            function onSession() {
              window.removeEventListener("financial-engine-session", onSession);
              resolve();
            }
            window.addEventListener("financial-engine-session", onSession);
          });
        });
      });
  }

  window.authReady
    .then(function () {
      return waitForSessionIfBearerRequired();
    })
    .then(function () {
      var sf = window.serverFetch || fetch;
      return sf(window.API_BASE + "/create_link_token");
    })
    .then(function (res) {
      if (!res.ok) throw new Error("HTTP " + res.status);
      return res.json();
    })
    .then(function (data) {
      var sf = window.serverFetch || fetch;
      plaidHandler = Plaid.create({
        token: data.link_token,
        onSuccess: function (public_token, metadata) {
          sf(window.API_BASE + "/exchange_public_token", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ public_token: public_token })
          })
            .then(parseApiResponse)
            .then(function () {
              return sf(window.API_BASE + "/sync_checking_accounts", { method: "POST" }).then(parseApiResponse);
            })
            .then(function () {
              return sf(window.API_BASE + "/sync_credit_accounts", { method: "POST" }).then(parseApiResponse);
            })
            .then(function () {
              return postLinkSyncTransactions(sf);
            })
            .then(function (txResult) {
              return ensureTransactionsAfterLink(sf, txResult);
            })
            .then(function (txResult) {
              if (typeof window.loadFinancialDashboard === "function") window.loadFinancialDashboard();
              var stored = num(txResult && txResult.stored);
              var fetched = num(txResult && txResult.fetched);
              var lines = [
                "Bank connected. Balances and accounts are saved first; transaction history is pulled from Plaid (with automatic retries if the first sync is empty)."
              ];
              lines.push("Last sync step: " + fetched + " from Plaid → " + stored + " new row(s) in your database.");
              if (stored === 0 && fetched > 0) {
                lines.push(
                  "Plaid returned transactions but none were inserted—check server logs (account_id mapping or DB constraints). You can still use the header refresh to retry."
                );
              } else if (stored === 0) {
                lines.push(
                  "No rows stored yet. Use the circular refresh in the header when ready, and confirm the Transactions product is enabled for your Plaid app."
                );
              } else {
                lines.push("Use the header refresh anytime to pull the latest from Plaid into this view.");
              }
              alert(lines.join("\n\n"));
            })
            .catch(function (err) {
              console.error("Error connecting bank:", err);
              alert(
                "Error while finishing bank link (exchange, sync accounts, or sync transactions):\n\n" +
                  (err && err.message ? err.message : String(err)) +
                  "\n\nIf the bank shows as linked but transaction rows stay at 0, use the circular refresh in the header or try Connect again after fixing the error above."
              );
            });
        },
        onExit: function (err, metadata) {
          if (err) console.log("Plaid exit:", err, metadata);
        },
        onError: function (err, metadata) {
          console.error("Plaid error:", err, metadata);
          alert("Plaid error: " + (err.error_message || err.display_message || "Unknown error"));
        }
      });
      linkTokenLoading = false;
      linkTokenLoadError = null;
      window.openPlaidLink = function () {
        if (plaidHandler) plaidHandler.open();
      };
    })
    .catch(function (err) {
      linkTokenLoading = false;
      linkTokenLoadError =
        "Could not open Plaid Link. GET " +
        window.API_BASE +
        "/create_link_token failed: " +
        (err && err.message ? err.message : String(err)) +
        "\n\nCheck: backend running on that host/port, browser Network tab, and server logs for Plaid errors.";
      console.error("Error fetching link token:", err);
    });
})();
