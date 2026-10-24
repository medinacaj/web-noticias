/* Reading controls; no dependencies, tracking, location or automatic movement. */
(function () {
  "use strict";
  var d = document, root = d.documentElement;
  var menu = d.getElementById("menu-toggle"), nav = d.getElementById("site-nav");
  var backdrop = d.getElementById("nav-backdrop");
  var desktop = window.matchMedia("(min-width: 1024px)");
  function remember(key, value) {
    try { localStorage.setItem(key, value); } catch (error) {}
  }
  function renderMenu() {
    if (!menu || !nav) return;
    var open = desktop.matches ? root.dataset.sidebar !== "hidden" : nav.classList.contains("open");
    menu.setAttribute("aria-expanded", String(open));
    menu.setAttribute("aria-label", open ? "Ocultar secciones" : "Mostrar secciones");
    if (backdrop) backdrop.hidden = desktop.matches || !open;
  }
  function setMenu(open) {
    if (!nav || desktop.matches) return;
    nav.classList.toggle("open", open);
    renderMenu();
  }
  window.NewsReader = {setMenu: setMenu};
  if (menu && nav) {
    menu.addEventListener("click", function () {
      if (desktop.matches) {
        root.dataset.sidebar = root.dataset.sidebar === "hidden" ? "visible" : "hidden";
        remember("noticias:sidebar:v1", root.dataset.sidebar);
        renderMenu();
      } else {
        setMenu(!nav.classList.contains("open"));
      }
    });
    nav.addEventListener("click", function (event) {
      if (event.target.closest("a")) setMenu(false);
    });
    if (backdrop) backdrop.addEventListener("click", function () { setMenu(false); menu.focus(); });
    d.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && nav.classList.contains("open")) {
        setMenu(false); menu.focus();
      }
    });
    desktop.addEventListener("change", function () {
      nav.classList.remove("open"); renderMenu();
    });
    renderMenu();
  }

  var systemTheme = window.matchMedia("(prefers-color-scheme: dark)");
  var themeSelect = d.getElementById("theme-select"), themeToggle = d.getElementById("theme-toggle");
  var themes = ["system", "light", "dark"];
  function applyTheme(preference) {
    if (themes.indexOf(preference) < 0) preference = "system";
    root.dataset.themePreference = preference;
    root.dataset.theme = preference === "system" ? (systemTheme.matches ? "dark" : "light") : preference;
    if (themeSelect) themeSelect.value = preference;
    if (themeToggle) {
      var label = {system: "automático", light: "claro", dark: "oscuro"};
      var next = themes[(themes.indexOf(preference) + 1) % themes.length];
      themeToggle.setAttribute("aria-label", "Tema " + label[preference] + ". Cambiar a " + label[next]);
      themeToggle.title = "Tema " + label[preference];
      themeToggle.querySelector("span").textContent = {system: "◐", light: "☀", dark: "☾"}[preference];
    }
  }
  if (themeSelect) themeSelect.addEventListener("change", function () {
    applyTheme(themeSelect.value); remember("noticias:theme:v1", themeSelect.value);
  });
  if (themeToggle) themeToggle.addEventListener("click", function () {
    var next = themes[(themes.indexOf(root.dataset.themePreference) + 1) % themes.length];
    applyTheme(next); remember("noticias:theme:v1", next);
  });
  systemTheme.addEventListener("change", function () { applyTheme(root.dataset.themePreference); });
  applyTheme(root.dataset.themePreference || "system");

  d.querySelectorAll("[data-carousel]").forEach(function (carousel) {
    var track = carousel.querySelector(".breaking-track"), controls = carousel.querySelector(".carousel-controls");
    var previous = carousel.querySelector("[data-carousel-prev]"), next = carousel.querySelector("[data-carousel-next]");
    var position = carousel.querySelector(".carousel-position");
    if (!track || !controls || !previous || !next) return;
    var reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    function update() {
      var max = track.scrollWidth - track.clientWidth;
      controls.hidden = max < 3;
      previous.disabled = track.scrollLeft <= 2;
      next.disabled = track.scrollLeft >= max - 2;
      var item = track.firstElementChild;
      var step = item ? item.getBoundingClientRect().width + 16 : 1;
      var first = Math.round(track.scrollLeft / step) + 1;
      var last = Math.min(track.children.length, first + Math.round((track.clientWidth + 16) / step) - 1);
      if (position) position.textContent = first + "–" + last + " de " + track.children.length;
    }
    function move(direction) {
      track.scrollBy({left: direction * (track.clientWidth + 16), behavior: reduced.matches ? "instant" : "smooth"});
    }
    previous.addEventListener("click", function () { move(-1); });
    next.addEventListener("click", function () { move(1); });
    track.addEventListener("keydown", function (event) {
      if (event.target !== track || ["ArrowLeft", "ArrowRight"].indexOf(event.key) < 0) return;
      event.preventDefault(); move(event.key === "ArrowRight" ? 1 : -1);
    });
    track.addEventListener("scroll", update, {passive: true});
    if ("ResizeObserver" in window) new ResizeObserver(update).observe(track);
    else window.addEventListener("resize", update);
    update();
  });
})();
