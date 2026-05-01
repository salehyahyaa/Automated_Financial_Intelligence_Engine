(function () {
  "use strict";

  var drawer = document.getElementById("nav-drawer");
  var toggle = document.getElementById("nav-toggle");
  var overlay = document.getElementById("nav-drawer-overlay");
  var closeBtn = document.getElementById("nav-drawer-close");

  if (!drawer || !toggle) return;

  function openDrawer() {
    drawer.classList.add("is-open");
    drawer.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  }

  function closeDrawer() {
    drawer.classList.remove("is-open");
    drawer.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }

  toggle.addEventListener("click", function () {
    if (drawer.classList.contains("is-open")) {
      closeDrawer();
    } else {
      openDrawer();
    }
  });

  if (overlay) overlay.addEventListener("click", closeDrawer);
  if (closeBtn) closeBtn.addEventListener("click", closeDrawer);

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && drawer.classList.contains("is-open")) {
      closeDrawer();
    }
  });

  // "Connect bank account" in drawer: open Plaid Link (same as chat dropdown action)
  var connectLink = drawer.querySelector('[data-action="connect-bank"]');
  if (connectLink) {
    connectLink.addEventListener("click", function (e) {
      e.preventDefault();
      closeDrawer();
      if (typeof window.openPlaidLink === "function") window.openPlaidLink();
    });
  }

  function setNavActive(action) {
    drawer.querySelectorAll(".nav-drawer-link[data-action]").forEach(function (a) {
      a.classList.toggle("nav-drawer-link--active", a.getAttribute("data-action") === action);
    });
  }

  drawer.querySelectorAll(".nav-drawer-link[data-action]").forEach(function (link) {
    link.addEventListener("click", function (e) {
      var action = link.getAttribute("data-action");
      if (!action) return;
      e.preventDefault();
      closeDrawer();

      if (action === "dashboard") {
        if (typeof window.navigateAppView === "function") window.navigateAppView("dashboard");
        else setNavActive("dashboard");
        return;
      }
      if (action === "settings") {
        if (typeof window.navigateAppView === "function") window.navigateAppView("settings");
        else setNavActive("settings");
        return;
      }
      if (action === "connected-accounts") {
        if (typeof window.navigateAppView === "function") {
          window.navigateAppView("connected-accounts");
        } else {
          setNavActive("connected-accounts");
        }
        return;
      }
    });
  });
})();
