"""Guías editoriales de cine/streaming de la semana, independientes de las noticias.

Una publicación reciente no acredita un estreno: sólo se admiten guías que
mencionan la semana o fechas de su intervalo. No se inventa un catálogo de obras.
"""
from datetime import datetime, time, timedelta
from html import escape
from itertools import islice
import re
import unicodedata
from urllib.parse import urlencode, urlsplit
from xml.etree.ElementTree import ParseError
from zoneinfo import ZoneInfo

from scripts.dedupe_history import canonical_key
from scripts.global_sources import matches_world_source
from scripts.latam import catalog_allowed, explicit_date

TZ = ZoneInfo('America/Santiago')
MONTHS = ('enero','febrero','marzo','abril','mayo','junio','julio','agosto',
          'septiembre','octubre','noviembre','diciembre')
SHORT_MONTHS = ('ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic')
# Identidades observadas en metadatos de Google Noticias, no feeds directos ni permisos.
SOURCES = (
    ('los40.cl','Chile','Cine'), ('culturizarte.cl','Chile','Cine'),
    ('adnradio.cl','Chile','Cine'), ('encancha.cl','Chile','Cine'),
    ('cinepremiere.com.mx','México','Streaming'), ('clarin.com','Argentina','Streaming'),
    ('espinof.com','España','Streaming'), ('as.com','España','Streaming'),
    ('sensacine.com','España','Streaming'),
)
PLATFORMS = (
    ('Netflix',r'\bnetflix\b'), ('Disney+',r'\bdisney(?:\s*plus|\+)?'),
    ('Prime Video',r'\b(?:amazon\s+)?prime\s+video\b'),
    ('HBO Max',r'\b(?:hbo\s+)?max\b'), ('Apple TV',r'\bapple\s+tv\b'),
    ('MUBI',r'\bmubi\b'), ('Filmin',r'\bfilmin\b'),
    ('Movistar Plus+',r'\bmovistar\s+plus'), ('SkyShowtime',r'\bskyshowtime\b'),
)
DATE = re.compile(r'\b(\d{1,2})(?:\s+al\s+(\d{1,2}))?\s+(?:de\s+)?('
                  +'|'.join(MONTHS)+r')(?:\s+(?:de\s+)?(20\d{2}))?\b')


def week_bounds(now):
    today=now.astimezone(TZ).date()
    monday=today-timedelta(days=today.weekday())
    return (datetime.combine(monday,time(),TZ),
            datetime.combine(monday+timedelta(days=7),time(),TZ))


def _fold(value):
    return ''.join(c for c in unicodedata.normalize('NFKD',value.casefold())
                   if not unicodedata.combining(c))


def _weekly_title(title,start,end):
    text=_fold(title)
    if (not re.search(r'\b(estrenos?|cartelera|que ver)\b',text)
            or re.search(r'\b(mejores|ranking|rankings|taquilla|top\s*\d+)\b',text)):
        return False
    dates=DATE.findall(text)
    if dates:
        for first,last,month,year in dates:
            years=[int(year)] if year else [start.year-1,start.year,start.year+1]
            for candidate in (first,last) if last else (first,):
                for y in years:
                    try:day=datetime(y,MONTHS.index(month)+1,int(candidate)).date()
                    except ValueError:continue
                    if start.date()<=day<end.date():return True
        return False
    return bool(re.search(r'\b(esta semana|de la semana|del? fin de semana|este fin de semana)\b',text))


def _prepare(item,now,restrictions):
    if not isinstance(item,dict):return None
    title=item.get('title');source=item.get('source');published=explicit_date(item.get('published'))
    start,end=week_bounds(now)
    if (not isinstance(title,str) or not title.strip() or len(title)>500
            or not isinstance(source,str) or not source.strip() or published is None
            or not start<=published<=now+timedelta(minutes=15) or published>=end
            or not _weekly_title(title,start,end)):
        return None
    try:host=(urlsplit(item.get('source_url')).hostname or '').lower().removeprefix('www.')
    except (TypeError,ValueError,AttributeError):return None
    identity=next((s for s in SOURCES if s[0]==host),None)
    if not identity or not matches_world_source(item,{'domain':host}) or not catalog_allowed(item,restrictions):
        return None
    folded=_fold(title)
    platforms=[label for label,pattern in PLATFORMS if re.search(pattern,folded)]
    kind='Streaming' if platforms else 'Cine'
    if kind=='Cine' and (identity[2]!='Cine' or not re.search(r'\b(cine|cines|cartelera)\b',folded)):
        return None
    from fetch_noticias import to_iso
    return {'title':title.strip(),'source':source.strip(),'source_url':item['source_url'],
            'link':item['link'],'published':to_iso(published),'market':identity[1],
            'platforms':platforms,'format':kind,'metadata_only':True,'summary':'','image':''}


def _restrictions():
    from scripts.global_sources import load_catalog as world
    from scripts.regional_sources import load_catalog as regional
    return world()+regional()


def collect_releases(now,fetch=None,restrictions=None):
    """Tres consultas al RSS existente, cuarenta resultados cada una, seis guías."""
    if fetch is None:
        from fetch_noticias import fetch_rss
        fetch=fetch_rss
    restrictions=_restrictions() if restrictions is None else restrictions
    start,end=week_bounds(now)
    sources=[s for s in SOURCES if catalog_allowed({'source_url':'https://'+s[0],
             'link':'https://'+s[0]},restrictions)]
    groups=([s for s in sources if s[2]=='Cine'],
            [s for s in sources if s[2]=='Streaming' and s[1]!='España'],
            [s for s in sources if s[2]=='Streaming' and s[1]=='España'])
    found={};seen=set()
    for group in groups:
        if not group:continue
        domains={s[0] for s in group}
        query='('+' OR '.join('site:'+s[0] for s in group)+') (estrenos OR cartelera OR "qué ver") '
        query+=f'after:{(start.date()-timedelta(days=1)).isoformat()} before:{end.date().isoformat()}'
        url='https://news.google.com/rss/search?'+urlencode({'q':query,'hl':'es-419','gl':'CL','ceid':'CL:es-419'})
        try:
            for item in islice(fetch(url,'cultura',metadata_only=True,limit=40) or [],40):
                record=_prepare(item,now,restrictions)
                if not record:continue
                host=(urlsplit(record['source_url']).hostname or '').lower().removeprefix('www.')
                if host not in domains:continue
                key=canonical_key(record['link']);bucket=found.setdefault(host,[])
                if key not in seen and len(bucket)<2:
                    seen.add(key);bucket.append(record)
        except (OSError,ValueError,TypeError,LookupError,ParseError) as error:
            print(f'[aviso] Guías de estrenos no disponibles: {type(error).__name__}')
    buckets=sorted(found.values(),key=lambda b:(b[0]['format']!='Cine',
                   b[0]['market']=='España',-explicit_date(b[0]['published']).timestamp()))
    result=[b[i] for i in range(2) for b in buckets if len(b)>i][:6]
    if result:print(f'Estrenos semanales: {len(result)} guías de {len({r["source_url"] for r in result})} medios')
    return result


def render_releases(items,now):
    """Las guías no se contabilizan como noticias ni como obras con estreno confirmado."""
    valid=[];seen=set()
    for item in items:
        record=_prepare(item,now,_restrictions())
        if record and (key:=canonical_key(record['link'])) not in seen:
            seen.add(key);valid.append(record)
        if len(valid)==6:break
    if not valid:return ''
    start,end=week_bounds(now);sunday=end-timedelta(days=1)
    label=f'{start.day} {SHORT_MONTHS[start.month-1]} – {sunday.day} {SHORT_MONTHS[sunday.month-1]}'
    cards=[]
    for record in valid:
        labels=record['platforms'][:2] or ['Cine en Chile']
        if len(record['platforms'])>2:labels.append('y más')
        stamp=explicit_date(record['published']).astimezone(TZ)
        cards.append('<li class="release-card"><article>'
            f'<p class="release-platform">{escape(" · ".join(labels))}</p>'
            f'<h4><a href="{escape(record["link"],quote=True)}" rel="noopener">{escape(record["title"])}</a></h4>'
            f'<p class="release-source">{escape(record["source"])} · Guía de {escape(record["market"])}</p>'
            f'<p class="release-date">Guía publicada <time datetime="{record["published"]}">'
            f'{stamp.day} {SHORT_MONTHS[stamp.month-1]}</time></p></article></li>')
    grid_class='release-grid release-grid--balanced' if len(valid) in (2,4) else 'release-grid'
    return ('<section class="weekly-releases" id="estrenos-semana" aria-labelledby="estrenos-titulo">'
            '<div class="releases-head"><h3 id="estrenos-titulo">Estrenos de la semana</h3>'
            f'<span>{label}</span></div>'
            '<p class="releases-intro">Cine, películas y series en streaming. Guías de medios; '
            'consulta fechas y disponibilidad para tu país en cada fuente.</p>'
            f'<ul class="{grid_class}">'+''.join(cards)+'</ul></section>')
