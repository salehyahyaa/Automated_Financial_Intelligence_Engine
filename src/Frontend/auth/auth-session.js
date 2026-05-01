/**
 * Optional Supabase Auth: meta supabase-url + supabase-anon-key on dashboard/dashboard.html,
 * or SUPABASE_URL + SUPABASE_ANON_KEY in API .env (fetched from GET /config/supabase-public).
 * Exposes window.authReady (Promise), window.apiFetchAuthorized, window.getAccessToken, window.supabaseAuth, window.serverFetch.
 */
(function () {
  function meta(name) {
    var m = document.querySelector('meta[name="' + name + '"]');
    return (m && m.getAttribute("content") && m.getAttribute("content").trim()) || "";
  }

  function apiBaseFromMeta() {
    var m = document.querySelector('meta[name="api-base"]');
    var b = (m && m.getAttribute("content") && m.getAttribute("content").trim()) || "http://127.0.0.1:8001";
    try {
      var u = new URL(b);
      if (u.port === "8000" && (u.hostname === "127.0.0.1" || u.hostname === "localhost")) {
        u.port = "8001";
      }
      return u.toString().replace(/\/+$/, "");
    } catch (e) {
      return "http://127.0.0.1:8001";
    }
  }

  function noSupabase() {
    window.getAccessToken = function () {
      return Promise.resolve(null);
    };
    window.apiFetchAuthorized = function (u, o) {
      return fetch(u, o || {});
    };
    window.supabaseAuth = null;
    window.serverFetch = function (u, o) {
      return fetch(u, o || {});
    };
  }

  function authSessionLog(payload) {
    if (typeof console !== "undefined" && console.info) {
      console.info("[FinancialEngine auth-session]", payload);
    }
  }

  function loadSupabaseClient(url, anon) {
    return import("https://esm.sh/@supabase/supabase-js@2").then(function (mod) {
      var client = mod.createClient(url, anon, {
        auth: {
          autoRefreshToken: true,
          persistSession: true,
          detectSessionInUrl: true,
        },
      });
      window.supabaseAuth = client;
      return client.auth.getSession().then(function (sess) {
        var has = !!(sess.data && sess.data.session);
        authSessionLog({ step: "initial_getSession", hasSession: has });
        window.getAccessToken = function () {
          return window.supabaseAuth.auth.getSession().then(function (r) {
            var s = r.data && r.data.session;
            return s ? s.access_token : null;
          });
        };
        window.apiFetchAuthorized = function (fetchUrl, opts) {
          opts = opts || {};
          return window.getAccessToken().then(function (token) {
            var method = (opts.method || "GET").toUpperCase();
            var hasBearer = !!token;
            authSessionLog({ step: "apiFetch", method: method, url: fetchUrl, hasBearer: hasBearer });
            var h = new Headers(opts.headers || {});
            if (token) h.set("Authorization", "Bearer " + token);
            return fetch(fetchUrl, Object.assign({}, opts, { headers: h })).then(function (res) {
              if (!res.ok && res.status === 401) {
                authSessionLog({ step: "apiFetch_401", url: fetchUrl, hasBearer: hasBearer });
              }
              return res;
            });
          });
        };
        window.serverFetch = function (fetchUrl, opts) {
          return window.apiFetchAuthorized(fetchUrl, opts);
        };
        return window.supabaseAuth;
      });
    });
  }

  function resolveSupabaseConfig() {
    var url = meta("supabase-url");
    var anon = meta("supabase-anon-key");
    if (url && anon) {
      return Promise.resolve({ url: url, anon: anon });
    }
    return fetch(apiBaseFromMeta() + "/config/supabase-public")
      .then(function (r) {
        if (!r.ok) return { url: url, anon: anon };
        return r.json();
      })
      .then(function (j) {
        return {
          url: url || String((j && j.supabase_url) || "").trim(),
          anon: anon || String((j && j.supabase_anon_key) || "").trim(),
        };
      })
      .catch(function () {
        return { url: url, anon: anon };
      });
  }

  window.authReady = resolveSupabaseConfig()
    .then(function (cfg) {
      if (!cfg.url || !cfg.anon) {
        noSupabase();
        return null;
      }
      return loadSupabaseClient(cfg.url, cfg.anon);
    })
    .catch(function (e) {
      console.error("Supabase client failed to load:", e);
      noSupabase();
      return null;
    });

  window.serverFetch = function (fetchUrl, opts) {
    return window.authReady.then(function () {
      return window.apiFetchAuthorized(fetchUrl, opts || {});
    });
  };
})();
