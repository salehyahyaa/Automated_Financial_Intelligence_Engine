/**
 * Auth gate (sign in / sign up), session label, sign-out. Uses financial-engine-session event for Plaid wait.
 * Supabase client resolves { data, error } — always check res.error (errors are not thrown).
 */
(function () {
  function el(id) {
    return document.getElementById(id);
  }

  function apiBase() {
    var m = document.querySelector('meta[name="api-base"]');
    var b = (m && m.getAttribute("content") && m.getAttribute("content").trim()) || "http://127.0.0.1:8001";
    try {
      var u = new URL(b);
      if (u.port === "8000" && (u.hostname === "127.0.0.1" || u.hostname === "localhost")) u.port = "8001";
      return u.toString().replace(/\/+$/, "");
    } catch (e) {
      return "http://127.0.0.1:8001";
    }
  }

  function fetchBearerRequired() {
    return fetch(apiBase() + "/config/auth-public")
      .then(function (r) {
        if (!r.ok) return { bearer_required: false };
        return r.json();
      })
      .catch(function () {
        return { bearer_required: false };
      });
  }

  function setGateMessage(text) {
    var n = el("auth-gate-message");
    if (n) n.textContent = text || "";
  }

  function authLog(tag, payload) {
    if (typeof console !== "undefined" && console.info) {
      console.info("[FinancialEngine auth]", tag, payload);
    }
  }

  function redirectForEmail() {
    return window.location.origin + window.location.pathname + (window.location.search || "");
  }

  function setLabel(text) {
    var emailEl = el("dash-profile-email");
    var cap = el("dash-profile-caption");
    var raw = text == null ? "" : String(text).trim();
    if (emailEl) {
      if (!raw || raw === "Not signed in") {
        emailEl.textContent = "Not signed in";
        if (cap) cap.textContent = "Account";
      } else {
        emailEl.textContent = raw;
        if (cap) cap.textContent = "Signed in as";
      }
    }
  }

  function showTabs(isSignIn) {
    var tIn = el("auth-tab-signin");
    var tUp = el("auth-tab-signup");
    var fIn = el("auth-gate-signin-form");
    var fUp = el("auth-gate-signup-form");
    if (tIn) {
      tIn.classList.toggle("auth-gate-tab--active", isSignIn);
      tIn.setAttribute("aria-selected", isSignIn ? "true" : "false");
    }
    if (tUp) {
      tUp.classList.toggle("auth-gate-tab--active", !isSignIn);
      tUp.setAttribute("aria-selected", isSignIn ? "false" : "true");
    }
    if (fIn) fIn.classList.toggle("auth-gate-form--hidden", !isSignIn);
    if (fUp) fUp.classList.toggle("auth-gate-form--hidden", isSignIn);
  }

  function setShellAuthed(authed) {
    document.body.classList.toggle("auth-shell-unlocked", !!authed);
  }

  function emitSession() {
    window.dispatchEvent(new CustomEvent("financial-engine-session"));
  }

  function refreshAfterAuth() {
    if (typeof window.loadFinancialDashboard === "function") window.loadFinancialDashboard();
    emitSession();
  }

  function applySessionUi() {
    if (!window.supabaseAuth) {
      setLabel("Not signed in");
      setShellAuthed(false);
      if (typeof window.refreshSettingsFromSession === "function") window.refreshSettingsFromSession();
      return;
    }
    window.supabaseAuth.auth.getSession().then(function (r) {
      var u = r.data && r.data.session && r.data.session.user;
      setLabel(u && u.email ? u.email : "Signed in");
      setShellAuthed(!!(r.data && r.data.session));
      if (typeof window.refreshSettingsFromSession === "function") window.refreshSettingsFromSession();
    });
  }

  function hideGate() {
    var g = el("auth-gate");
    if (g) g.classList.add("auth-gate--hidden");
    document.body.classList.remove("auth-gate-active");
  }

  function showGate() {
    var g = el("auth-gate");
    if (g) g.classList.remove("auth-gate--hidden");
    document.body.classList.add("auth-gate-active");
  }

  function syncGate() {
    setGateMessage("");
    fetchBearerRequired().then(function (cfg) {
      if (!cfg.bearer_required) {
        hideGate();
        applySessionUi();
        if (typeof window.loadFinancialDashboard === "function") window.loadFinancialDashboard();
        emitSession();
        return;
      }
      if (!window.supabaseAuth) {
        showGate();
        setGateMessage("Configure SUPABASE_URL and SUPABASE_ANON_KEY in the API .env, then restart the server.");
        setShellAuthed(false);
        return;
      }
      window.supabaseAuth.auth.getSession().then(function (r) {
        if (r.data && r.data.session) {
          hideGate();
          applySessionUi();
          refreshAfterAuth();
        } else {
          showGate();
          setShellAuthed(false);
          setLabel("Not signed in");
        }
      });
    });
  }

  window.authReady.then(function () {
    syncGate();
    if (!window.supabaseAuth) return;
    window.supabaseAuth.auth.onAuthStateChange(function (_evt, session) {
      applySessionUi();
      if (session) {
        hideGate();
        refreshAfterAuth();
      } else {
        fetchBearerRequired().then(function (cfg) {
          if (cfg.bearer_required) {
            showGate();
            if (typeof window.loadFinancialDashboard === "function") {
              var ld = document.getElementById("dash-loading");
              var dc = document.getElementById("dash-content");
              if (dc) dc.classList.add("dash-content--hidden");
              if (ld) {
                ld.textContent = "Sign in to load your dashboard.";
                ld.classList.remove("dash-content--hidden");
              }
            }
          }
        });
      }
    });
  });

  document.addEventListener("DOMContentLoaded", function () {
    el("auth-tab-signin") &&
      el("auth-tab-signin").addEventListener("click", function () {
        showTabs(true);
        setGateMessage("");
      });
    el("auth-tab-signup") &&
      el("auth-tab-signup").addEventListener("click", function () {
        showTabs(false);
        setGateMessage("");
      });

    var formIn = el("auth-gate-signin-form");
    if (formIn) {
      formIn.addEventListener("submit", function (e) {
        e.preventDefault();
        if (!window.supabaseAuth) {
          setGateMessage("Supabase is not configured on this deployment.");
          return;
        }
        var email = (el("auth-gate-email-in") && el("auth-gate-email-in").value) || "";
        var pass = (el("auth-gate-password-in") && el("auth-gate-password-in").value) || "";
        setGateMessage("Signing in…");
        window.supabaseAuth.auth.signInWithPassword({ email: email.trim(), password: pass }).then(function (res) {
          authLog("signIn", { email: email.trim(), error: res.error && res.error.message, hasSession: !!(res.data && res.data.session) });
          if (res.error) {
            var em = res.error.message || String(res.error);
            if (/confirm|verified|verification/i.test(em)) {
              em += " — use “Resend confirmation email” below, or check spam.";
            }
            setGateMessage(em);
            return;
          }
          setGateMessage("");
          hideGate();
          applySessionUi();
          refreshAfterAuth();
        });
      });
    }

    var formUp = el("auth-gate-signup-form");
    if (formUp) {
      formUp.addEventListener("submit", function (e) {
        e.preventDefault();
        if (!window.supabaseAuth) {
          setGateMessage("Supabase is not configured on this deployment.");
          return;
        }
        var email = (el("auth-gate-email-up") && el("auth-gate-email-up").value) || "";
        var pass = (el("auth-gate-password-up") && el("auth-gate-password-up").value) || "";
        setGateMessage("Creating account…");
        var emailRedirectTo = redirectForEmail();
        window.supabaseAuth.auth
          .signUp({
            email: email.trim(),
            password: pass,
            options: { emailRedirectTo: emailRedirectTo },
          })
          .then(function (res) {
            authLog("signUp", {
              email: email.trim(),
              error: res.error && res.error.message,
              hasSession: !!(res.data && res.data.session),
              hasUser: !!(res.data && res.data.user),
            });
            if (res.error) {
              var msg = res.error.message || String(res.error);
              if (/already|registered|exists/i.test(msg)) {
                msg += " — open the Sign in tab and log in, or remove the user in Supabase → Authentication → Users and try again.";
              }
              setGateMessage(msg);
              return;
            }
            if (res.data && res.data.session) {
              setGateMessage("");
              hideGate();
              applySessionUi();
              refreshAfterAuth();
            } else {
              setGateMessage(
                "If this email is new, Supabase sent a confirmation link (check spam). If you already used this email, open Sign in — no second email is sent for duplicate sign-ups."
              );
              showTabs(true);
            }
          });
      });
    }

    var resendBtn = el("auth-resend-confirmation");
    if (resendBtn) {
      resendBtn.addEventListener("click", function () {
        if (!window.supabaseAuth) return;
        var email = (el("auth-gate-email-in") && el("auth-gate-email-in").value) || "";
        if (!email.trim()) {
          setGateMessage("Enter your email in the Sign in form first.");
          return;
        }
        setGateMessage("Sending confirmation…");
        window.supabaseAuth.auth
          .resend({ type: "signup", email: email.trim(), options: { emailRedirectTo: redirectForEmail() } })
          .then(function (res) {
            authLog("resend", { email: email.trim(), error: res.error && res.error.message });
            if (res.error) {
              setGateMessage(res.error.message || String(res.error));
              return;
            }
            setGateMessage("If an unconfirmed account exists for that email, Supabase sent another message. Check spam.");
          });
      });
    }

    var out = el("auth-signout-btn");
    if (out) {
      out.addEventListener("click", function () {
        if (!window.supabaseAuth) return;
        window.supabaseAuth.auth.signOut().then(function () {
          applySessionUi();
          syncGate();
        });
      });
    }
  });
})();
