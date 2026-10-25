"""Señales editoriales basadas solo en titulares, enlaces, fechas y medios.
Adaptación aislada del enfoque de RadarRRS; no rastrea lectores ni copia artículos.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from math import sqrt
import re
import unicodedata
from urllib.parse import urlsplit

MAX_ARCHIVE = 2000
ARCHIVE_DAYS = 8
REFERENCE_DAYS = 7
STOPWORDS = set("""
a al algo ante antes aqui asi aun cada casi como con contra cual cuando de del desde donde
dos durante el ella ellos en entre era es esa ese eso esta este esto estos fue fueron ha
han hasta hay hoy la las le les lo los mas me mientras muy ni no nos o otra otro para
pero por porque que quien se segun ser si sin sobre son su sus tambien tan tras tres
un una uno unos y ya año años dia dias semana semanas mes meses hora horas minuto minutos
vez veces parte caso casos forma tiempo mundo pais paises dicen dijo afirma anuncia
anuncio revela explica advierte confirma pide busca llega deja tiene hace puede sera
seria estan gobierno presidente ministro nacional general mayor primer primera ultimo ultima
ultimas ultimos noticias noticia video fotos foto directo vivo ayer manana
enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre
lunes martes miercoles jueves viernes sabado domingo
chile venezuela latinoamerica america internacional tecnologia
futbol football basquetbol tenis deporte deportes deportivo partido partidos encuentro
encuentros marcador marcadores resultado resultados goles gol victoria victorias derrota
derrotas empate empates jornada jornadas fecha fechas liga ligas copa copas campeonato
campeonatos torneo torneos equipos equipo jugador jugadores jugadora temporada temporadas
sabe analisis opinion columna editorial entrevista resumen cronica reportaje especial
the a an and are as at be by for from has have how in into is it its new of on
or that this to was what when why will with you your
""".split())


def fold(text):
    return "".join(ch for ch in unicodedata.normalize("NFKD", str(text or "").casefold())
                   if not unicodedata.combining(ch))


def moment(raw):
    try:
        dt = datetime.fromisoformat(str(raw or "").replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except (ValueError, TypeError, OverflowError):
        return None


def canonical(url):
    try:
        p = urlsplit(str(url or "").strip())
        if p.scheme != "https" or not p.hostname or p.username or p.password or p.port not in (None, 443):
            return ""
        from scripts.dedupe_history import canonical_key
        return canonical_key(url)
    except (ValueError, TypeError):
        return ""


def update_archive(previous, recent, now):
    """Historial compacto, estable e idempotente; no altera la portada de 24h."""
    records = {}
    cutoff = now - timedelta(days=ARCHIVE_DAYS)
    for story in list(previous or []) + list(recent or []):
        if not isinstance(story, dict):
            continue
        key = canonical(story.get("link"))
        dt = moment(story.get("published")) or moment(story.get("first_seen"))
        title = str(story.get("title") or "").strip()
        category = str(story.get("category") or "")
        if not key or not title or not category or not dt or dt < cutoff or dt > now + timedelta(minutes=30):
            continue
        sources = [s.strip()[:90] for s in story.get("sources", []) if isinstance(s, str) and s.strip()]
        if not sources:
            continue
        entry = records.get(key)
        if entry is None:
            records[key] = {
                "title": title[:230], "link": str(story["link"])[:1200],
                "category": category, "published": dt.isoformat().replace("+00:00", "Z"),
                "sources": list(dict.fromkeys(sources))[:12],
            }
        else:
            entry["sources"] = list(dict.fromkeys(entry["sources"] + sources))[:12]
            if dt < moment(entry["published"]):
                entry["published"] = dt.isoformat().replace("+00:00", "Z")
    return sorted(records.values(), key=lambda e: e["published"], reverse=True)[:MAX_ARCHIVE]


def terms(title):
    words = []
    for raw in re.findall(r"[\wÀ-ÿ]+", title or ""):
        word = fold(raw)
        words.append(word if len(word) >= 4 and not word.isdigit() and word not in STOPWORDS else "")
    result = {w for w in words if w}
    result.update(a + " " + b for a, b in zip(words, words[1:]) if a and b)
    return result


def trending_topics(archive, now, started_at, limit=5):
    """No afirmar tendencias hasta disponer de siete días completos de referencia."""
    start = moment(started_at)
    # La comparación utiliza 24 h actuales + siete días COMPLETOS anteriores:
    # requiere ocho días de capturas, no siete, y datos desde el inicio.
    if start is None or now - start < timedelta(days=ARCHIVE_DAYS):
        return []
    dated = [moment(item.get("published")) for item in archive]
    dated = [dt for dt in dated if dt is not None]
    if not dated or min(dated) > now - timedelta(days=ARCHIVE_DAYS) + timedelta(hours=6):
        return []
    current_start = now - timedelta(hours=24)
    baseline_start = current_start - timedelta(days=REFERENCE_DAYS)
    current, baseline = Counter(), Counter()
    outlets, examples = defaultdict(set), {}
    for article in archive:
        when = moment(article.get("published"))
        if when is None or when < baseline_start or when > now:
            continue
        key = canonical(article.get("link"))
        if not key:
            continue
        for term in terms(article.get("title")):
            if when >= current_start:
                current[term] += 1
                outlets[term].update(fold(s).strip() for s in article.get("sources", []) if s)
                if term not in examples or when > examples[term][0]:
                    examples[term] = (when, article)
            else:
                baseline[term] += 1
    ranked = []
    for term, count in current.items():
        if count < 4 or len(outlets[term]) < 4:
            continue
        previous_daily = baseline[term] / REFERENCE_DAYS
        strength = (count - previous_daily) / sqrt(previous_daily + 1)
        if strength >= 2:
            ranked.append((strength + (0.2 if " " in term else 0), term))
    ranked.sort(reverse=True)
    result, covered = [], set()
    for _, term in ranked:
        tokens = set(term.split())
        if tokens & covered:
            continue
        item = examples[term][1]
        result.append({
            "label": term, "stories": current[term],
            "sources": len(outlets[term]),
            "previous_daily": round(baseline[term] / REFERENCE_DAYS, 1),
            "link": item["link"],
        })
        covered.update(tokens)
        if len(result) >= limit:
            break
    return result


def related_timeline(archive, now, limit=1):
    """Candidatos conservadores: titulares casi idénticos en fechas diferentes."""
    recent = [x for x in archive if moment(x.get("published"))
              and now - timedelta(hours=24) <= moment(x["published"]) <= now]
    result = []
    for lead in recent[:35]:
        title = fold(lead.get("title"))
        lead_time = moment(lead.get("published"))
        group = [lead]
        for other in archive:
            when = moment(other.get("published"))
            if (other is lead or not when or canonical(other.get("link")) == canonical(lead.get("link"))
                    or other.get("category") != lead.get("category")
                    or abs((when - lead_time).total_seconds()) < 6 * 3600):
                continue
            other_title = fold(other.get("title"))
            if title and SequenceMatcher(None, title, other_title).ratio() >= 0.9:
                group.append(other)
        if len(group) < 2 or len({s for item in group for s in item.get("sources", [])}) < 2:
            continue
        group.sort(key=lambda x: x["published"])
        result.append(group[-4:])
        if len(result) >= limit:
            break
    return result


def render_signals(trends, timeline):
    """HTML mínimo y accesible, sin tarjetas extra ni etiquetas inventadas."""
    from html import escape
    esc = lambda value: escape(str(value or ""), quote=True)
    sections = []
    if trends:
        entries = "".join(
            '<li><a href="' + esc(x["link"]) + '" rel="noopener">'
            + esc(x["label"]) + '</a><span>' + str(x["stories"]) + ' publicaciones · '
            + str(x["sources"]) + ' medios</span></li>' for x in trends)
        sections.append(
            '<section class="coverage-radar" aria-labelledby="trends-title">'
            '<div class="radar-head"><h2 id="trends-title">Temas en alza</h2>'
            '<span>Comparación con 7 días</span></div>'
            '<p>Mayor presencia de estos términos en titulares recientes. '
            'Mínimo cuatro publicaciones de cuatro medios; no representa popularidad entre lectores.</p>'
            '<ul>' + entries + '</ul></section>')
    if timeline:
        for index, group in enumerate(timeline):
            entries = "".join(
                '<li><time datetime="' + esc(x["published"]) + '">' + esc(x["published"][:16].replace("T", " "))
                + ' UTC</time><a href="' + esc(x["link"]) + '" rel="noopener">'
                + esc(x["title"]) + '</a></li>' for x in group)
            sections.append(
                '<section class="coverage-radar signal-timeline" aria-labelledby="timeline-title-'
                + str(index) + '"><div class="radar-head"><h2 id="timeline-title-' + str(index)
                + '">Seguimiento de publicaciones</h2><span>Historial de titulares</span></div>'
                '<p>Notas de distintos medios con titulares muy semejantes en momentos diferentes. '
                'La coincidencia no demuestra que describan exactamente el mismo hecho.</p>'
                '<ul>' + entries + '</ul></section>')
    return "".join(sections)

