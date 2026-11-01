/* Reading controls; no dependencies, tracking, location or automatic movement. */
(function () {
  "use strict";
  var d = document, root = d.documentElement;
  var menu = d.getElementById("menu-toggle"), nav = d.getElementById("site-nav");
  var backdrop = d.getElementById("nav-backdrop");
  var edge = d.getElementById("sidebar-edge");
  var desktop = window.matchMedia("(min-width: 1024px)");
  var headerActions = d.getElementById("header-actions"), navTools = d.getElementById("nav-tools");
  var viewWrap = d.querySelector(".view-options-wrap"), savedToggle = d.getElementById("library-toggle");
  function placeTools() {
    if (!headerActions || !navTools || !viewWrap || !savedToggle) return;
    var active = d.activeElement, movingFocus = viewWrap.contains(active) || savedToggle === active;
    var panel = viewWrap.querySelector(".view-options-panel");
    var focusInPanel = panel && panel.contains(active), viewToggle = viewWrap.querySelector("button");
    if (panel) panel.hidden = true;
    viewToggle.setAttribute("aria-expanded", "false");
    var target = desktop.matches ? headerActions : navTools;
    target.appendChild(viewWrap); target.appendChild(savedToggle);
    navTools.hidden = desktop.matches;
    if (movingFocus) (desktop.matches ? (focusInPanel ? viewToggle : active) : menu).focus({preventScroll:true});
  }
  placeTools();
  function remember(key, value) {
    try { localStorage.setItem(key, value); } catch (error) {}
  }
  function renderMenu() {
    if (!menu || !nav) return;
    var open = desktop.matches ? root.dataset.sidebar !== "hidden" : nav.classList.contains("open");
    menu.setAttribute("aria-expanded", String(open));
    menu.setAttribute("aria-label", open ? "Ocultar secciones" : "Mostrar secciones");
    root.dataset.menuOpen = String(!desktop.matches && open);
    if (edge) {
      edge.setAttribute("aria-expanded", String(open));
      edge.setAttribute("aria-label", open ? "Ocultar barra lateral" : "Mostrar barra lateral");
      edge.title = open ? "Ocultar barra lateral" : "Mostrar barra lateral";
      edge.querySelector("path").setAttribute("d", open ? "m14 6-6 6 6 6" : "m10 6 6 6-6 6");
    }
    if (backdrop) backdrop.hidden = desktop.matches || !open;
  }
  function setMenu(open) {
    if (!nav || desktop.matches) return;
    nav.classList.toggle("open", open);
    renderMenu();
    if (open) {
      nav.scrollTop = 0;
      var firstSection = nav.querySelector("a");
      if (firstSection) firstSection.focus({preventScroll: true});
    }
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
    if (edge) edge.addEventListener("click", function () {
      menu.click();
      if (!desktop.matches) menu.focus();
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
    d.addEventListener("focusin", function (event) {
      if (!desktop.matches && nav.classList.contains("open")
          && !event.target.closest("#site-nav,#menu-toggle,#sidebar-edge,.site-header")) {
        setMenu(false);
      }
    });
    desktop.addEventListener("change", function () {
      placeTools(); nav.classList.remove("open"); renderMenu();
    });
    renderMenu();
  }

  var systemTheme = window.matchMedia("(prefers-color-scheme: dark)");
  var themeSelect = d.getElementById("theme-select"), themeToggle = d.getElementById("theme-toggle");
  var themes = ["system", "light", "dark"];
  function applyTheme(preference) {
    if (themes.indexOf(preference) < 0) preference = "light";
    root.dataset.themePreference = preference;
    root.dataset.theme = preference === "system" ? (systemTheme.matches ? "dark" : "light") : preference;
    var themeMeta = d.querySelector('meta[name="theme-color"]');
    if (themeMeta) themeMeta.setAttribute("content", root.dataset.theme === "dark" ? "#111315" : "#E9E8E2");
    if (themeSelect) themeSelect.value = preference;
    if (themeToggle) {
      var label = {system: "automático", light: "claro", dark: "oscuro"};
      var next = root.dataset.theme === "dark" ? "light" : "dark";
      themeToggle.setAttribute("aria-label", "Tema " + label[preference] + ". Cambiar a " + label[next]);
      themeToggle.title = "Activar tema " + label[next];
      themeToggle.querySelector("span").innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        + (next === "dark" ? '<path d="M20.7 13.1A8.5 8.5 0 0 1 10.9 3.3 8.5 8.5 0 1 0 20.7 13.1Z"/>'
          : '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4m0-14.2-1.4 1.4M6.3 17.7l-1.4 1.4"/>') + '</svg>';
    }
  }
  if (themeSelect) themeSelect.addEventListener("change", function () {
    applyTheme(themeSelect.value); remember("noticias:theme:v1", themeSelect.value);
  });
  if (themeToggle) themeToggle.addEventListener("click", function () {
    var next = root.dataset.theme === "dark" ? "light" : "dark";
    applyTheme(next); remember("noticias:theme:v1", next);
  });
  systemTheme.addEventListener("change", function () { applyTheme(root.dataset.themePreference); });
  applyTheme(root.dataset.themePreference || "light");

  d.querySelectorAll("[data-carousel]").forEach(function (carousel) {
    var track = carousel.querySelector(".breaking-track");
    var pause = carousel.querySelector("[data-carousel-pause]");
    if (!track) return;
    if (pause) {
      pause.hidden = false;
      var staticLabel = carousel.querySelector("[data-breaking-label]");
      if (staticLabel) staticLabel.hidden = true;
    }
    var reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    var count = track.children.length;
    if (count > 1) {
      var clone = track.firstElementChild.cloneNode(true);
      clone.dataset.carouselClone = "true";
      clone.setAttribute("aria-hidden", "true");
      clone.querySelectorAll("[id]").forEach(function (el) { el.removeAttribute("id"); });
      clone.querySelectorAll("a,button").forEach(function (el) { el.tabIndex = -1; });
      track.appendChild(clone);
      track.classList.add("is-sliding");
    }
    var frame = null, lastTime = null, offset = track.scrollLeft;
    var userPlay = null, hovering = false, focused = false;
    function wantsPlay() { return userPlay === null ? !reduced.matches : userPlay; }
    function canPlay() {
      return pause && wantsPlay() && !hovering && !focused && !d.hidden
        && count > 1 && track.clientWidth > 0;
    }
    function index() {
      return Math.max(0, Math.min(count - 1,
        Math.round(track.scrollLeft / Math.max(1, track.clientWidth))));
    }
    function schedule() {
      if (frame !== null) window.cancelAnimationFrame(frame);
      frame = null; lastTime = null; offset = track.scrollLeft;
      var active = canPlay();
      if (pause) {
        pause.disabled = count <= 1;
        pause.setAttribute("aria-label", wantsPlay() ? "Pausar deslizamiento de Lo último" : "Reanudar deslizamiento de Lo último");
        pause.setAttribute("aria-pressed", String(!wantsPlay()));
        pause.title = wantsPlay() ? "Pausar carrusel" : "Reanudar carrusel";
      }
      if (active) frame = window.requestAnimationFrame(tick);
    }
    function tick(time) {
      frame = null;
      if (!canPlay()) { schedule(); return; }
      // Velocidad constante, independiente de la frecuencia de pantalla.
      if (lastTime !== null) offset += Math.min(time - lastTime, 50) * 0.04;
      lastTime = time;
      var length = count * track.clientWidth;
      if (offset >= length) offset %= length;
      track.scrollLeft = offset;
      update();
      frame = window.requestAnimationFrame(tick);
    }

    function update() {
      if (pause) pause.disabled = count <= 1;
    }

    function move(direction) {
      var target = Math.max(0, Math.min(count - 1, index() + direction));
      track.scrollTo({left: target * track.clientWidth, behavior: reduced.matches ? "instant" : "smooth"});
      schedule();
    }
    if (pause) pause.addEventListener("click", function () {
      userPlay = !wantsPlay();
      // Reanudar es una petición explícita, aun si el botón conserva el foco.
      if (userPlay) { hovering = false; focused = false; }
      schedule();
    });
    carousel.addEventListener("mouseenter", function () { hovering = true; schedule(); });
    track.addEventListener("mouseenter", function () { hovering = true; schedule(); });
    carousel.addEventListener("mouseleave", function () { hovering = false; schedule(); });
    carousel.addEventListener("focusin", function () { focused = true; schedule(); });
    carousel.addEventListener("focusout", function (event) {
      if (!carousel.contains(event.relatedTarget)) { focused = false; schedule(); }
    });
    d.addEventListener("visibilitychange", schedule);
    reduced.addEventListener("change", function (event) {
      if (event.matches && userPlay === true) userPlay = null;
      schedule();
    });
    track.addEventListener("keydown", function (event) {
      if (event.target !== track || ["ArrowLeft", "ArrowRight"].indexOf(event.key) < 0) return;
      event.preventDefault(); move(event.key === "ArrowRight" ? 1 : -1);
    });
    track.addEventListener("scroll", function () {
      // Conservar fracciones de píxel del avance; sincronizar gestos manuales.
      if (Math.abs(track.scrollLeft - offset) > 2) offset = track.scrollLeft;
      update();
    }, {passive: true});
    function resized() { update(); schedule(); }
    if ("ResizeObserver" in window) new ResizeObserver(resized).observe(track);
    else window.addEventListener("resize", resized);
    update(); schedule();
  });
})();
