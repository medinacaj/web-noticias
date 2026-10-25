/* Novedades de la edición; un único valor local, sin historial de lectura. */
(function () {
  "use strict";
  var main = document.getElementById("contenido");
  var time = document.getElementById("updated-at");
  var button = document.getElementById("visit-updates");
  if (!main || !time || !button) return;
  var edition = Date.parse(time.dateTime);
  if (!Number.isFinite(edition)) return;
  var key = "noticias:last-edition:v1:" + location.pathname.replace(/index\.html$/, "");
  var previous;
  try {
    previous = Number(localStorage.getItem(key));
    if (!Number.isFinite(previous) || previous <= 0 || previous > Date.now()) previous = 0;
    if (edition > previous) localStorage.setItem(key, String(edition));
  } catch (error) { return; }
  if (!previous || previous >= edition) return;

  var entries = [], ids = new Set();
  main.querySelectorAll(".lead,.feature,.rail-list li,.compact-list li").forEach(function (card) {
    var link = card.querySelector("h2 a[data-first-seen],h3 a[data-first-seen]");
    if (!link) return;
    var seen = Date.parse(link.dataset.firstSeen), id = link.dataset.newsId;
    if (!id || ids.has(id) || !Number.isFinite(seen) || seen <= previous || seen > edition) return;
    ids.add(id);
    var metadata = card.querySelector(".meta");
    if (metadata) {
      var badge = document.createElement("span");
      badge.className = "new-story-label";
      badge.textContent = "Nueva";
      badge.title = "Incorporada al sitio desde tu visita anterior";
      metadata.appendChild(badge);
    }
    entries.push({card: card, link: link});
  });
  var matching = [], cursor = 0;
  function refresh() {
    matching = entries.filter(function (entry) {
      return !entry.card.closest("[data-source-hidden],[data-filtered],[hidden]");
    });
    button.hidden = !matching.length;
    button.textContent = matching.length + (matching.length === 1 ? " nueva · Ver" : " nuevas · Ver");
    button.title = "Incorporadas al sitio desde tu visita anterior, según tus filtros";
    button.setAttribute("aria-label", "Ver " + matching.length + " noticias incorporadas desde tu visita anterior");
    cursor = 0;
  }
  button.addEventListener("click", function () {
    if (!matching.length) return;
    var entry = matching[cursor++ % matching.length];
    var grid = entry.card.closest(".section-grid");
    if (grid && entry.card.hasAttribute("data-extra")) {
      var more = document.querySelector('[data-show-more][aria-controls="' + grid.id + '"]');
      for (var i = 0; i < 70 && more && !more.hidden && entry.card.hasAttribute("data-extra"); i++) more.click();
    }
    entry.link.focus({preventScroll: true});
    entry.card.scrollIntoView({block: "center", behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth"});
  });
  document.addEventListener("change", refresh);
  main.addEventListener("news-preferences-change", refresh);
  refresh();
})();
