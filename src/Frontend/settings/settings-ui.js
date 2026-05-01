/**
 * Settings + connected-accounts panel + navigation.
 * window.navigateAppView("dashboard" | "settings" | "connected-accounts", options?), window.refreshSettingsFromSession().
 */
(function () {
  "use strict";

  function el(id) {
    return document.getElementById(id);
  }

  /** Match dashboard.js / plaid: same host as summary so /linked-accounts never hits the static server on :8000. */
  function apiBase() {
    var b =
      window.API_BASE ||
      ((document.querySelector('meta[name="api-base"]') || {}).content || "").trim() ||
      "http://127.0.0.1:8001";
    b = String(b).replace(/\/+$/, "");
    if (!/^https?:\/\//i.test(b)) {
      b = "http://127.0.0.1:8001";
    }
    try {
      var u = new URL(b);
      if (u.port === "8000" && (u.hostname === "127.0.0.1" || u.hostname === "localhost")) {
        u.port = "8001";
        b = u.toString().replace(/\/+$/, "");
      } else {
        b = u.toString().replace(/\/+$/, "");
      }
    } catch (e) {
      b = "http://127.0.0.1:8001";
    }
    return b;
  }

  function redirectForEmail() {
    return window.location.origin + window.location.pathname + (window.location.search || "");
  }

  function setInputValue(id, value) {
    var n = el(id);
    if (n) n.value = value == null ? "" : String(value);
  }

  function setMsg(id, text, isError) {
    var n = el(id);
    if (!n) return;
    n.textContent = text || "";
    n.classList.toggle("settings-msg--error", !!isError && !!text);
  }

  function displayNameFromUser(user) {
    if (!user || !user.user_metadata) return "";
    var m = user.user_metadata;
    return (m.full_name || m.name || m.display_name || "").trim();
  }

  function refreshSettingsFromSession() {
    var lead = el("settings-profile-lead");
    var emailIn = el("settings-email");
    var nameIn = el("settings-display-name");
    if (!emailIn) return;

    if (!window.supabaseAuth) {
      if (lead) lead.textContent = "Supabase auth is not configured. Profile and password tools need the API Supabase keys.";
      setInputValue("settings-email", "");
      if (nameIn) nameIn.value = "";
      [emailIn, nameIn].forEach(function (node) {
        if (node) node.disabled = true;
      });
      return;
    }

    [emailIn, nameIn].forEach(function (node) {
      if (node) node.disabled = false;
    });

    window.supabaseAuth.auth.getSession().then(function (r) {
      var session = r.data && r.data.session;
      var user = session && session.user;
      if (!user) {
        if (lead) lead.textContent = "Sign in to manage your profile and password.";
        setInputValue("settings-email", "");
        if (nameIn) nameIn.value = "";
        return;
      }
      if (lead) lead.textContent = "Signed in. Update your display name or password below.";
      setInputValue("settings-email", user.email || "");
      if (nameIn && document.activeElement !== nameIn) {
        nameIn.value = displayNameFromUser(user);
      }
    });
  }

  window.refreshSettingsFromSession = refreshSettingsFromSession;

  function loadLinkedAccountsInto(list, hint, msg) {
    if (!list) return;
    if (msg) {
      msg.textContent = "";
      msg.classList.remove("settings-msg--error");
    }
    list.innerHTML = "";
    if (hint) hint.textContent = "Loading linked accounts…";

    function renderError(text) {
      if (hint) hint.textContent = "Could not load linked accounts.";
      if (msg) {
        msg.textContent = (hint ? "" : "Could not load linked accounts. ") + (text || "");
        msg.classList.toggle("settings-msg--error", !!text);
      }
    }

    function runFetch() {
      if (typeof window.serverFetch !== "function") {
        if (hint) hint.textContent = "Linked accounts load after the page finishes initializing.";
        else if (msg) msg.textContent = "Linked accounts load after the page finishes initializing.";
        return;
      }
      window
        .serverFetch(apiBase() + "/linked-accounts", { method: "GET" })
        .then(function (r) {
          return r.json().then(function (j) {
            return { r: r, j: j };
          });
        })
        .then(function (x) {
          if (!x.r.ok) {
            var d = x.j && x.j.detail;
            renderError(typeof d === "string" ? d : JSON.stringify(d || x.r.statusText));
            return;
          }
          var accounts = (x.j && x.j.accounts) || [];
          if (hint) hint.textContent = "";
          if (accounts.length === 0) {
            var p = document.createElement("p");
            p.className = "settings-linked-empty";
            p.textContent =
              "No linked banks yet. Use the chat menu → Connect bank account, then use the header refresh to sync.";
            list.appendChild(p);
            return;
          }
          accounts.forEach(function (a) {
            var row = document.createElement("div");
            row.className = "settings-linked-row";
            row.setAttribute("role", "listitem");
            var info = document.createElement("div");
            info.className = "settings-linked-info";
            var title = document.createElement("div");
            title.className = "settings-linked-title";
            title.textContent = ((a.name || "Account") + "").trim() || "Account";
            var meta = document.createElement("div");
            meta.className = "settings-linked-meta";
            var bits = [];
            if (a.institution) bits.push(String(a.institution));
            if (a.bank && String(a.bank) !== String(a.institution || "")) bits.push(String(a.bank));
            if (a.account_type) bits.push(String(a.account_type));
            if (a.mask) bits.push("····" + String(a.mask));
            meta.textContent = bits.join(" · ");
            info.appendChild(title);
            info.appendChild(meta);
            var btn = document.createElement("button");
            btn.type = "button";
            btn.className = "settings-linked-delbtn";
            btn.textContent = "Delink";
            btn.addEventListener("click", function () {
              delinkAccountRow(a, btn, msg);
            });
            row.appendChild(info);
            row.appendChild(btn);
            list.appendChild(row);
          });
        })
        .catch(function () {
          renderError("Network error loading linked accounts.");
        });
    }

    if (window.authReady) window.authReady.then(runFetch);
    else runFetch();
  }

  function loadConnectedAccountsPanel() {
    loadLinkedAccountsInto(el("connected-accounts-list"), null, el("connected-accounts-msg"));
  }

  window.loadConnectedAccountsPanel = loadConnectedAccountsPanel;

  function delinkAccountRow(a, btn, msg) {
    var inst = a.institution || a.bank || "this bank";
    var accName = (a.name || "account").trim() || "account";
    if (
      !confirm(
        'Permanently remove the bank connection that includes "' +
          inst +
          " — " +
          accName +
          '"? All accounts from that same Plaid login will be deleted from Financial Engine along with their stored data. You will need to connect through Plaid again to add them back.'
      )
    ) {
      return;
    }
    btn.disabled = true;
    var msgNode = msg || el("connected-accounts-msg");
    if (msgNode) {
      msgNode.textContent = "Removing…";
      msgNode.classList.remove("settings-msg--error");
    }
    window
      .serverFetch(apiBase() + "/linked-accounts/" + encodeURIComponent(String(a.id)), { method: "DELETE" })
      .then(function (r) {
        return r.json().then(function (j) {
          return { r: r, j: j };
        });
      })
      .then(function (x) {
        btn.disabled = false;
        if (!x.r.ok) {
          var d = x.j && x.j.detail;
          if (msgNode) {
            msgNode.textContent = typeof d === "string" ? d : x.r.statusText;
            msgNode.classList.add("settings-msg--error");
          }
          return;
        }
        if (msgNode) {
          msgNode.textContent =
            "Connection removed. Those accounts are no longer in the system—use Connect bank account if you want to link again.";
          msgNode.classList.remove("settings-msg--error");
        }
        loadConnectedAccountsPanel();
        window.dispatchEvent(new CustomEvent("financial-engine-session"));
        if (typeof window.loadFinancialDashboard === "function") window.loadFinancialDashboard();
      })
      .catch(function () {
        btn.disabled = false;
        if (msgNode) {
          msgNode.textContent = "Network error while removing link.";
          msgNode.classList.add("settings-msg--error");
        }
      });
  }

  function navigateAppView(view, options) {
    options = options || {};
    var dash = el("dashboard-main");
    var settings = el("view-settings");
    var connected = el("view-connected-accounts");
    if (!dash || !settings) return;

    var links = document.querySelectorAll(".nav-drawer-link[data-action]");

    function hideSettingsAndConnected() {
      settings.classList.add("settings-panel--hidden");
      settings.setAttribute("aria-hidden", "true");
      if (connected) {
        connected.classList.add("settings-panel--hidden");
        connected.setAttribute("aria-hidden", "true");
      }
    }

    if (view === "dashboard") {
      hideSettingsAndConnected();
      dash.classList.remove("dashboard-main--hidden");
      dash.setAttribute("aria-hidden", "false");
      links.forEach(function (a) {
        a.classList.toggle("nav-drawer-link--active", a.getAttribute("data-action") === "dashboard");
      });
      return;
    }

    dash.classList.add("dashboard-main--hidden");
    dash.setAttribute("aria-hidden", "true");

    if (view === "connected-accounts") {
      if (!connected) {
        navigateAppView("dashboard");
        return;
      }
      settings.classList.add("settings-panel--hidden");
      settings.setAttribute("aria-hidden", "true");
      connected.classList.remove("settings-panel--hidden");
      connected.setAttribute("aria-hidden", "false");
      loadConnectedAccountsPanel();
      links.forEach(function (a) {
        a.classList.toggle("nav-drawer-link--active", a.getAttribute("data-action") === "connected-accounts");
      });
      return;
    }

    if (view === "settings") {
      if (connected) {
        connected.classList.add("settings-panel--hidden");
        connected.setAttribute("aria-hidden", "true");
      }
      settings.classList.remove("settings-panel--hidden");
      settings.setAttribute("aria-hidden", "false");
      refreshSettingsFromSession();
      links.forEach(function (a) {
        a.classList.toggle("nav-drawer-link--active", a.getAttribute("data-action") === "settings");
      });
    }
  }

  window.navigateAppView = navigateAppView;

  document.addEventListener("DOMContentLoaded", function () {
    var nameIn = el("settings-display-name");

    var saveProfile = el("settings-save-profile");
    if (saveProfile) {
      saveProfile.addEventListener("click", function () {
        setMsg("settings-profile-msg", "");
        if (!window.supabaseAuth) {
          setMsg("settings-profile-msg", "Supabase is not configured.", true);
          return;
        }
        var name = (nameIn && nameIn.value) || "";
        setMsg("settings-profile-msg", "Saving…");
        window.supabaseAuth.auth
          .updateUser({ data: { full_name: name.trim(), name: name.trim() } })
          .then(function (res) {
            if (res.error) {
              setMsg("settings-profile-msg", res.error.message || String(res.error), true);
              return;
            }
            setMsg("settings-profile-msg", "Profile saved.");
            window.dispatchEvent(new CustomEvent("financial-engine-session"));
          });
      });
    }

    var changePw = el("settings-change-password");
    if (changePw) {
      changePw.addEventListener("click", function () {
        setMsg("settings-auth-msg", "");
        if (!window.supabaseAuth) {
          setMsg("settings-auth-msg", "Supabase is not configured.", true);
          return;
        }
        var p1 = (el("settings-new-password") && el("settings-new-password").value) || "";
        var p2 = (el("settings-confirm-password") && el("settings-confirm-password").value) || "";
        if (p1.length < 6) {
          setMsg("settings-auth-msg", "Password must be at least 6 characters.", true);
          return;
        }
        if (p1 !== p2) {
          setMsg("settings-auth-msg", "Passwords do not match.", true);
          return;
        }
        setMsg("settings-auth-msg", "Updating password…");
        window.supabaseAuth.auth.updateUser({ password: p1 }).then(function (res) {
          if (res.error) {
            setMsg("settings-auth-msg", res.error.message || String(res.error), true);
            return;
          }
          setMsg("settings-auth-msg", "Password updated.");
          setInputValue("settings-new-password", "");
          setInputValue("settings-confirm-password", "");
        });
      });
    }

    var resetBtn = el("settings-reset-email-btn");
    if (resetBtn) {
      resetBtn.addEventListener("click", function () {
        setMsg("settings-auth-msg", "");
        if (!window.supabaseAuth) {
          setMsg("settings-auth-msg", "Supabase is not configured.", true);
          return;
        }
        window.supabaseAuth.auth.getSession().then(function (r) {
          var email = r.data && r.data.session && r.data.session.user && r.data.session.user.email;
          if (!email) {
            setMsg("settings-auth-msg", "No email on this session.", true);
            return;
          }
          setMsg("settings-auth-msg", "Sending reset email…");
          window.supabaseAuth.auth
            .resetPasswordForEmail(email.trim(), { redirectTo: redirectForEmail() })
            .then(function (res) {
              if (res.error) {
                setMsg("settings-auth-msg", res.error.message || String(res.error), true);
                return;
              }
              setMsg("settings-auth-msg", "If the account exists, check your inbox for a reset link.");
            });
        });
      });
    }

    var so = el("settings-signout-btn");
    if (so) {
      so.addEventListener("click", function () {
        var top = el("auth-signout-btn");
        if (top) top.click();
        else if (window.supabaseAuth) {
          window.supabaseAuth.auth.signOut();
        }
        navigateAppView("dashboard");
      });
    }

    window.addEventListener("financial-engine-session", function () {
      var settings = el("view-settings");
      var connected = el("view-connected-accounts");
      if (settings && !settings.classList.contains("settings-panel--hidden")) {
        refreshSettingsFromSession();
      }
      if (connected && !connected.classList.contains("settings-panel--hidden")) {
        loadConnectedAccountsPanel();
      }
    });
  });
})();
