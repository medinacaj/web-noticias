"""Lecturas y temas: selección determinista de metadatos, sin nuevas consultas."""
from collections import Counter
from datetime import timedelta
from difflib import SequenceMatcher
from hashlib import sha256
from html import escape
import re
from zoneinfo import ZoneInfo

from scripts.editorial_signals import canonical, fold, moment, terms
from scripts.newsletter import safe_external_url
from scripts.presentation_groups import canonical_section, PRESENTATION_LABELS
from scripts.source_diversity import publisher_key
from scripts.reading_topics import story_topics

MONTHS = ('ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic')
UTILITY = re.compile(r'\b(subsidios?|bonos?|beneficios?|tramites?|plazos?|postulacion|postulaciones|tarifas?|combustibles?|precios?|empleos?|sueldos?|salarios?|pensiones|transporte|alerta sae|evacuacion)\b')
esc = lambda value: escape(str(value or ''), quote=True)


def _eligible(stories, now, hours=24):
    from scripts.satire import is_satire
    seen, result = set(), []
    for item in stories or []:
        if not isinstance(item, dict) or item.get('content_kind') or is_satire(item):
            continue
        title, sources = item.get('title'), item.get('sources')
        when = moment(item.get('published'))
        url = safe_external_url(item.get('link'))
        key = canonical(url)
        if (not isinstance(title,str) or not title.strip() or len(title)>500 or not key
                or key in seen or not when or not now-timedelta(hours=hours)<=when<=now
                or not isinstance(sources,list) or not any(isinstance(s,str) and s.strip() for s in sources)):
            continue
        seen.add(key);result.append(item)
    return result


def _rank(item, now):
    sources = {s for s in item['sources'] if isinstance(s,str) and s.strip()}
    return (len(sources)-(now-moment(item['published'])).total_seconds()/21600,
            moment(item['published']),canonical(item['link']))


def _diverse(items, now, limit):
    candidates = sorted(items,key=lambda item:_rank(item,now),reverse=True)
    chosen, sections, counts, seen = [], set(), Counter(), set()
    for item in candidates:
        section, publisher = canonical_section(item['category']), publisher_key(item)
        if section in sections or counts[publisher]:continue
        chosen.append(item);sections.add(section);counts[publisher]+=1;seen.add(id(item))
        if len(chosen)>=limit:return chosen[:limit]
    for quota in (2,limit):
        for item in candidates:
            publisher=publisher_key(item)
            if id(item) in seen or counts[publisher]>=quota:continue
            chosen.append(item);seen.add(id(item));counts[publisher]+=1
            if len(chosen)>=limit:return chosen[:limit]
    return chosen[:max(0,limit)]


def select_brief(stories, now, limit=5):
    return _diverse(_eligible(stories,now),now,max(0,limit)) if limit>0 else []


def useful_stories(stories, now, limit=6):
    candidates=[s for s in _eligible(stories,now) if s.get('category') in
                ('nacional','politica','regiones','economia','medioambiente') and UTILITY.search(fold(s['title']))]
    return _diverse(candidates,now,limit)


def discover_stories(stories, now, limit=6):
    candidates=[s for s in _eligible(stories,now) if s.get('category') in
                ('tecnologia','salud-ciencia','medioambiente','cultura') or 'startups' in story_topics(s)]
    return _diverse(candidates,now,limit)


def build_topics(stories, archive, now):
    """Relacionar titulares muy próximos; referencias adicionales siempre aparte."""
    from scripts.related_news import display_coverages
    records=_eligible(list(stories or [])+list(archive or []),now,hours=8*24)[:2000]
    # Las páginas se conservan durante la misma ventana del historial, no solo
    # mientras un tema está entre los primeros de la portada.
    candidates=sorted(records,key=lambda s:_rank(s,now),reverse=True)
    info={id(s):(fold(s['title']),{t for t in terms(s['title']) if ' ' not in t}) for s in records}
    result, used = [], set()
    for lead in candidates:
        key=canonical(lead['link'])
        if key in used:continue
        title, tokens=info[id(lead)]
        group=[lead]
        for item in records:
            other_key=canonical(item['link'])
            if other_key==key or other_key in used or item['category']!=lead['category']:continue
            other_title, other_tokens=info[id(item)]
            if len(tokens & other_tokens)<2:continue
            comparison=SequenceMatcher(None,title,other_title)
            if comparison.quick_ratio()>=.88 and comparison.ratio()>=.88:group.append(item)
        references, links=[], {canonical(s['link']) for s in group}
        for item in group:
            rows,_=display_coverages(item,[],now=None)
            for row in rows:
                when=moment(row.get('published'));url=canonical(row.get('link'))
                if url and url not in links and when and now-timedelta(days=8)<=when<=now:
                    references.append(row);links.add(url)
        sources=list(dict.fromkeys(s.strip() for item in group for s in item['sources'] if isinstance(s,str) and s.strip()))
        if len(sources)<4 and len(group)<2 and not references:continue
        # Cada URL permite conservar su página aunque cambie el orden editorial.
        identifier=sha256(repr(key).encode()).hexdigest()[:16]
        group.sort(key=lambda item:moment(item['published']))
        result.append({'id':identifier,'lead':lead,'entries':group,'sources':sources,
                       'aliases':[sha256(repr(canonical(s['link'])).encode()).hexdigest()[:16] for s in group],
                       'references':sorted(references,key=lambda r:moment(r['published']))[:12]})
        used.update(canonical(s['link']) for s in group)
    return result


def _date(raw):
    when=moment(raw).astimezone(ZoneInfo('America/Santiago'))
    return f'{when.day} {MONTHS[when.month-1]} {when.year}, {when:%H:%M}'


def _entry(story, labels):
    sources=[s for s in story.get('sources',[]) if isinstance(s,str) and s.strip()]
    source=story.get('source') or ', '.join(sources[:3])+ (f' y {len(sources)-3} más' if len(sources)>3 else '')
    category=labels.get(story.get('category'),'Referencia relacionada')
    return (f'<li class="reading-card"><article><p class="eyebrow">{esc(category)}</p>'
            f'<h3><a href="{esc(story["link"])}" rel="noopener">{esc(story["title"])}</a></h3>'
            f'<p class="byline">{esc(source)} · <time datetime="{esc(story["published"])}">{_date(story["published"])}</time></p>'
            '</article></li>')


def _section(identifier,title,description,items,labels,*,numbered=False):
    if not items:return ''
    tag='ol' if numbered else 'ul'
    return (f'<section id="{identifier}" aria-labelledby="title-{identifier}"><div class="reading-section-head">'
            f'<h2 id="title-{identifier}">{title}</h2><p>{description}</p></div>'
            f'<{tag} class="reading-list{" brief-list" if numbered else ""}">'
            +''.join(_entry(s,labels) for s in items)+f'</{tag}></section>')


def _page(title,description,body,base,canonical_url):
    return (f'<!doctype html><html lang="es" data-theme="light"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="robots" content="noindex,follow">'
            f'<title>{esc(title)} · Noticias del Momento</title><meta name="description" content="{esc(description)}">'
            f'<link rel="canonical" href="{esc(canonical_url)}"><link rel="icon" href="{esc(base)}/favicon.svg">'
            f'<link rel="stylesheet" href="{esc(base)}/reading-pages.css">'
            f'<script src="{esc(base)}/reading-pages.js" defer></script></head><body>'
            '<a class="skip-link" href="#contenido">Saltar al contenido</a>'
            '<header class="reading-header"><div class="reading-wrap reading-header-inner">'
            f'<a class="reading-brand" href="{esc(base)}/"><img src="{esc(base)}/logo-simbolo.svg?v=editorial" width="32" height="32" alt="">Noticias del Momento</a>'
            '<div class="reading-controls"><label for="reading-size">Texto<select id="reading-size"><option value="small">Pequeño</option><option value="normal" selected>Normal</option><option value="large">Grande</option></select></label>'
            '<button id="reading-theme" type="button" aria-label="Cambiar al modo oscuro">◐</button></div></div></header>'
            f'<main class="reading-wrap" id="contenido"><nav class="breadcrumb" aria-label="Ruta de navegación"><a href="{esc(base)}/">Portada</a><span aria-hidden="true">/</span><a href="{esc(base)}/hoy.html">Hoy</a></nav>'
            +body+f'</main><footer class="reading-footer"><div class="reading-wrap"><p>Titulares y referencias con enlaces a los medios originales. Las fechas corresponden a su publicación, en hora de Santiago.</p>'
            f'<a href="{esc(base)}/">Volver a la portada</a>'
            '<a class="designer-signature" href="https://www.linkedin.com/in/medinacaj/" target="_blank" rel="noopener noreferrer"><span>Diseñado por</span> <strong>@medinacaj</strong> ✦ ↗</a></div></footer></body></html>')


def render_discovery_pages(stories,archive,now,site_url,categories,*,topics=None):
    base=site_url.rstrip('/')
    labels={c['key']:c['label'] for c in categories}
    topics=build_topics(stories,archive,now) if topics is None else topics
    brief=select_brief(stories,now)
    useful=useful_stories(stories,now)
    discoveries=discover_stories(stories,now)
    active=[t for t in topics if moment(t['lead']['published'])>=now-timedelta(hours=24)][:5]
    destinations=[('resumen','El día en 2 minutos')]
    if useful:destinations.append(('para-ti','Qué cambia para ti'))
    if active:destinations.append(('seguimiento','En seguimiento'))
    if discoveries:destinations.append(('descubre','Descubre'))
    body=(f'<p class="eyebrow">Edición del {_date(now.isoformat())} · Santiago</p><h1>Tu día, en perspectiva</h1>'
          '<p class="reading-intro">Una selección breve para informarte, encontrar noticias útiles y explorar otros temas.</p>'
          '<nav class="reading-tabs" aria-label="Lecturas de hoy">'+''.join(f'<a href="#{key}">{label}</a>' for key,label in destinations)+'</nav>')
    body+=_section('resumen','El día en 2 minutos','Cinco titulares de las últimas 24 horas, con diversidad de temas y fuentes.',brief,labels,numbered=True)
    if not brief:body+='<section id="resumen"><p>No hay titulares recientes disponibles. Puedes consultar la portada y el archivo.</p></section>'
    body+=_section('para-ti','Qué cambia para ti','Precios, empleo, trámites y otros asuntos prácticos. Consulta los detalles y requisitos en el medio original.',useful,labels)
    if active:
        links=''.join(f'<li class="reading-card"><p class="eyebrow">{len(t["sources"])} medios registrados</p>'
                      f'<h3><a href="{esc(base)}/temas/{t["id"]}.html">{esc(t["lead"]["title"])}</a></h3>'
                      '<p class="byline">Ver publicaciones y referencias</p></li>' for t in active)
        body+='<section id="seguimiento"><div class="reading-section-head"><h2>Temas en seguimiento</h2><p>Coberturas agrupadas y sus fechas originales.</p></div><ul class="reading-list">'+links+'</ul></section>'
    body+=_section('descubre','Descubre','Ciencia, cultura e innovación para ampliar la mirada.',discoveries,labels)
    body+=('<aside class="official-resources" aria-labelledby="resources-title"><h2 id="resources-title">Consultas útiles en Chile</h2>'
           '<a href="https://www.meteochile.gob.cl/" rel="noopener">Consultar clima · Dirección Meteorológica de Chile ↗</a>'
           '<a href="https://www.bcentral.cl/" rel="noopener">Consultar dólar, UF e indicadores · Banco Central ↗</a></aside>')
    files={'hoy.html':_page('Hoy','Resumen y lecturas de la edición actual.',body,base,base+'/hoy.html')}
    for topic in topics:
        lead=topic['lead'];path='temas/'+topic['id']+'.html'
        body=(f'<p class="eyebrow">Temas en seguimiento · últimos 8 días</p><h1>{esc(lead["title"])}</h1>'
              '<p class="reading-intro">Publicaciones con titulares próximos dentro de una misma sección. Consulta cada fuente para conocer su información completa.</p>'
              f'<p class="topic-sources"><strong>{len(topic["sources"])} medios registrados:</strong> {esc(", ".join(topic["sources"]))}</p>')
        body+=_section('publicaciones','Publicaciones del tema','Ordenadas por fecha de publicación, de la primera a la más reciente.',topic['entries'],labels,numbered=True)
        body+=_section('referencias','Referencias relacionadas','Otros enfoques; estas referencias no se suman a los medios que respaldan el titular principal.',topic['references'],labels)
        for identifier in dict.fromkeys([topic['id']]+topic['aliases']):
            alias='temas/'+identifier+'.html'
            files[alias]=_page(lead['title'],'Publicaciones y referencias de un tema, con sus fechas y medios originales.',body,base,base+'/'+path)
    return files
