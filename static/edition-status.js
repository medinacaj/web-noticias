/* Reloj GMT y consulta manual de la edición pública; sin credenciales ni rastreo. */
(function () {
  "use strict";
  var d = document;
  var edition = d.getElementById("updated-at"), clock = d.getElementById("site-clock");
  var progress = d.getElementById("refresh-progress"), fill = d.getElementById("refresh-fill");
  var button = d.getElementById("refresh-now"), notice = d.getElementById("refresh-status");
  var help = d.getElementById("refresh-help");
  if (!edition || !clock || !progress || !fill || !button || !notice || !help) return;
  var published = Date.parse(edition.dateTime);
  var minute = Number(progress.dataset.refreshMinute);
  if (!Number.isInteger(minute) || minute < 0 || minute > 59) minute = 7;
  var scheduled = new Date(published);
  scheduled.setUTCMinutes(minute, 0, 0);
  if (scheduled.getTime() <= published) scheduled.setUTCHours(scheduled.getUTCHours() + 1);
  var deadline = scheduled.getTime(), noticeTimer, helpTimer;
  function hideHelp() { window.clearTimeout(helpTimer); help.hidden = true; }
  function showHelp() {
    window.clearTimeout(helpTimer);
    notice.hidden = true;
    help.hidden = false;
  }
  function leaveHelp() {
    helpTimer = window.setTimeout(function () {
      if (d.activeElement !== progress && !help.matches(":hover") && !progress.matches(":hover")) hideHelp();
    }, 180);
  }
  progress.addEventListener("mouseenter", showHelp);
  progress.addEventListener("mouseleave", leaveHelp);
  progress.addEventListener("focus", showHelp);
  progress.addEventListener("blur", hideHelp);
  progress.addEventListener("click", function () { progress.focus({preventScroll: true}); showHelp(); });
  help.addEventListener("mouseenter", showHelp);
  help.addEventListener("mouseleave", leaveHelp);
  d.addEventListener("pointerdown", function (event) {
    if (!progress.contains(event.target) && !help.contains(event.target)) hideHelp();
  });
  d.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && !help.hidden) { hideHelp(); event.stopPropagation(); }
  }, true);
  function pad(number) { return String(number).padStart(2, "0"); }
  function tick() {
    var now = new Date();
    clock.textContent = pad(now.getUTCHours()) + ":" + pad(now.getUTCMinutes()) + " GMT";
    clock.dateTime = now.toISOString();
    clock.setAttribute("aria-label", "Hora actual: " + clock.textContent + " (UTC+0)");
    var remaining = deadline - now.getTime(), message, percent = 0;
    if (!Number.isFinite(deadline)) {
      message = "Horario de actualización no disponible. Puedes comprobar si hay noticias nuevas.";
    } else {
      percent = Math.max(0, Math.min(100, 100 - remaining / 3600000 * 100));
      message = remaining > 0
        ? "Próxima actualización prevista en " + Math.ceil(remaining / 60000) + " min. La publicación puede demorarse."
        : "Actualización prevista pendiente de publicación. Puedes comprobar si hay noticias nuevas.";
    }
    fill.style.width = percent + "%";
    progress.setAttribute("aria-valuenow", String(Math.round(percent)));
    progress.setAttribute("aria-valuetext", message);
    help.textContent = message;
  }
  function announce(message) {
    hideHelp();
    window.clearTimeout(noticeTimer);
    notice.textContent = message;
    notice.hidden = false;
    noticeTimer = window.setTimeout(function () { notice.hidden = true; }, 6000);
  }
  button.addEventListener("click", async function () {
    if (button.disabled) return;
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
    notice.hidden = true;
    notice.textContent = "";
    var controller = new AbortController();
    var timeout = window.setTimeout(function () { controller.abort(); }, 10000);
    try {
      // Archivo mínimo de la misma publicación, no consulta APIs del recolector.
      var endpoint = new URL("edition.json", window.location.href);
      endpoint.searchParams.set("edition_check", String(Date.now()));
      var response = await fetch(endpoint.href, {
        cache: "no-store", credentials: "omit", redirect: "error", signal: controller.signal
      });
      if (!response.ok) throw new Error("Edition unavailable");
      var data = await response.json();
      var next = data && typeof data.updated === "string" ? Date.parse(data.updated) : NaN;
      if (!Number.isFinite(next) || !Number.isFinite(published)) throw new Error("Invalid edition");
      if (next > published) {
        announce("Hay una edición más reciente. Cargando…");
        // Guardar antes de iniciar la recarga; pagehide llega después de su captura.
        d.dispatchEvent(new Event("news:save-view"));
        var destination = new URL(window.location.href);
        destination.searchParams.set("edition", String(next));
        window.history.replaceState(window.history.state, "", destination.href);
        window.location.reload();
      } else {
        announce("No hay una edición más reciente disponible.");
      }
    } catch (error) {
      announce("No se pudo comprobar la actualización. Inténtalo de nuevo.");
    } finally {
      window.clearTimeout(timeout);
      button.disabled = false;
      button.setAttribute("aria-busy", "false");
    }
  });
  tick();
  window.setInterval(tick, 1000);
  d.addEventListener("visibilitychange", function () { if (!d.hidden) tick(); });
})();
