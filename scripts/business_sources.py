"""Descubrimiento empresarial por el RSS Google Noticias ya usado por el portal.

El registro acredita identidades en el índice, no permisos editoriales. No activa
feeds directos ni modifica los catálogos opt-in o sus restricciones existentes.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from html import escape
from itertools import islice
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlencode, urlsplit
from xml.etree.ElementTree import ParseError

from scripts.article_images import permitted_url
from scripts.dedupe_history import canonical_key
from scripts.global_sources import matches_world_source
from scripts.latam import catalog_allowed, explicit_date

CATALOG = Path(__file__).resolve().parents[1] / 'config/business_sources.json'
MAX_QUERIES = 12
DOMAINS_PER_QUERY = 12
MAX_ITEMS_PER_SOURCE = 2
MAX_ITEMS = 80
GROUPS = {
    'startups':'Startups e inversión', 'corporate':'Gestión y empresas',
    'b2b':'Tecnología empresarial', 'business_media':'Prensa económica y tecnología',
    'academic':'Investigación académica',
}
TERMS = {
    'startups':'(startup OR startups OR inversión OR financiamiento OR fintech OR venture OR funding OR innovación)',
    'corporate':'(empresas OR negocios OR digital OR innovación OR emprendimiento OR management OR tecnología)',
    'b2b':'(tecnología OR software OR ciberseguridad OR nube OR digital OR telecomunicaciones OR IA)',
    'business_media':'(startup OR innovación OR digital OR tecnología OR software OR inteligencia artificial OR fintech)',
}


def load_catalog(path=CATALOG):
    return json.loads(Path(path).read_text(encoding='utf-8'))['sources']


def _publisher_url(value, domain):
    return (isinstance(value,str) and not any(c.isspace() or c=='\\' for c in value)
            and permitted_url(value,check_dns=False)
            and matches_world_source({'source_url':value,'link':value.rstrip('/')+'/identity'}, {'domain':domain}))


def _eligible(source, restrictions):
    if not isinstance(source,dict):return False
    domain=source.get('domain');evidence=source.get('evidence') or {};group=source.get('group')
    scope=source.get('search_scope',domain)
    if (source.get('discovery_enabled') is not True or source.get('identity_status')!='indexed'
            or source.get('kind') not in ('news','analysis','institutional')
            or source.get('category') not in ('economia','tecnologia')
            or not isinstance(group,str) or group not in TERMS or not isinstance(domain,str)
            or not re.fullmatch(r'[a-z0-9.-]+',domain)
            or not isinstance(source.get('id'),str) or not source['id'].strip()
            or not isinstance(source.get('name'),str) or not source['name'].strip()
            or not isinstance(scope,str) or not _publisher_url('https://'+scope,domain)
            or not isinstance(evidence,dict) or not _publisher_url(evidence.get('source_url'),domain)
            or not _publisher_url(source.get('url'),domain)):
        return False
    return catalog_allowed({'source_url':source['url'],'link':source['url'],
                            'source':source.get('name')},restrictions)


def _key(link):
    try:return canonical_key(link) if isinstance(link,str) else None
    except (TypeError,ValueError):return None


def _queries(sources, now):
    plans=[]
    for group,terms in TERMS.items():
        group_sources=[s for s in sources if s['group']==group]
        for start in range(0,len(group_sources),DOMAINS_PER_QUERY):
            batch=group_sources[start:start+DOMAINS_PER_QUERY]
            query='('+' OR '.join('site:'+s.get('search_scope',s['domain']) for s in batch)+') '+terms+' when:1d'
            plans.append(('https://news.google.com/rss/search?'+urlencode({
                'q':query,'hl':'es-419','gl':'CL','ceid':'CL:es-419'}),batch))
    if len(plans)>MAX_QUERIES:
        offset=(now.hour*MAX_QUERIES)%len(plans)
        plans=(plans+plans)[offset:offset+MAX_QUERIES]
    return plans


def _fold(text):
    return ''.join(c for c in unicodedata.normalize('NFKD',text.casefold()) if not unicodedata.combining(c))


def _record(item,source,now,restrictions):
    from fetch_noticias import to_iso
    if not isinstance(item,dict):return None
    title=item.get('title');published=explicit_date(item.get('published'))
    if (not isinstance(title,str) or not title.strip() or len(title)>500 or published is None
            or not now-timedelta(hours=24)<=published<=now+timedelta(minutes=15)
            or not matches_world_source(item,source) or not catalog_allowed(item,restrictions)):
        return None
    expected=(urlsplit(source['evidence']['source_url']).hostname or '').lower().removeprefix('www.')
    observed=(urlsplit(item['source_url']).hostname or '').lower().removeprefix('www.')
    if observed!=expected:return None
    if item.get('source') is not None and not isinstance(item['source'],str):return None
    folded=_fold(title)
    if re.search(r'\b(casino|apuestas|betting|slots|contenido patrocinado|sponsored content)\b',folded):return None
    if source['group']=='business_media' and not re.search(
            r'\b(startups?|digital\w*|tecnolog\w*|innov\w*|software|fintech|ciber\w*|'
            r'inteligencia artificial|ia|cloud|nube|ecommerce|emprend\w*|pagos)\b',folded):
        return None
    if folded.strip(' .:|-')==_fold(source['name']).strip(' .:|-'):return None
    return {'title':title.strip(),'link':item['link'],'source':item.get('source') or source['name'],
            'source_url':item['source_url'],'published':to_iso(published),
            'category':source['category'],'publisher_id':source['id'],
            'source_kind':source['kind'],'metadata_only':True,'summary':'','image':''}


def collect_business(now,fetch=None,catalog=None,restrictions=None,existing=()):
    """Hasta 12 consultas al proveedor existente; sin llamadas a artículos/GNews."""
    if fetch is None:
        from fetch_noticias import fetch_rss
        fetch=fetch_rss
    if restrictions is None:
        from scripts.global_sources import load_catalog as world_catalog
        from scripts.regional_sources import load_catalog as regional_catalog
        restrictions=world_catalog()+regional_catalog()
    sources=[s for s in (load_catalog() if catalog is None else catalog) if _eligible(s,restrictions)]
    # Una identidad por dominio evita multiplicar presupuesto por alias del editor.
    sources=list({s['domain']:s for s in sources}.values())
    plans=_queries(sources,now)
    if not plans:return []
    def read(plan):
        url,batch=plan
        try:
            return batch,list(islice(fetch(url,batch[0]['category'],metadata_only=True,limit=60) or [],60))
        except (OSError,ValueError,TypeError,LookupError,ParseError) as error:
            print(f'[aviso] Búsqueda empresarial no disponible: {type(error).__name__}')
            return batch,[]
    seen={key for r in existing if isinstance(r,dict) and (key:=_key(r.get('link')))}
    buckets={s['id']:[] for s in sources}
    with ThreadPoolExecutor(max_workers=min(3,len(plans))) as pool:
        for batch,items in pool.map(read,plans):
            for item in items:
                for source in batch:
                    record=_record(item,source,now,restrictions)
                    if record is None:continue
                    key=canonical_key(record['link'])
                    bucket=buckets[source['id']]
                    if key not in seen and len(bucket)<MAX_ITEMS_PER_SOURCE:
                        seen.add(key);bucket.append(record)
                    break
    populated=[bucket for bucket in buckets.values() if bucket]
    if len(populated)>MAX_ITEMS:
        offset=(now.hour*MAX_ITEMS)%len(populated)
        populated=populated[offset:]+populated[:offset]
    result=[bucket[position] for position in range(MAX_ITEMS_PER_SOURCE)
            for bucket in populated if len(bucket)>position][:MAX_ITEMS]
    if result:print(f'Fuentes de negocios: {len(result)} titulares de {len({r["publisher_id"] for r in result})} editores')
    return result


def render_directory(catalog=None):
    """Directorio de consulta: enlaces al editor; ninguna noticia de ejemplo."""
    sources=load_catalog() if catalog is None else catalog
    groups=[]
    kinds={'news':'Medio','analysis':'Análisis','institutional':'Institucional','academic':'Revista'}
    pending=[]
    for group,label in GROUPS.items():
        entries=[]
        for source in sources:
            if source.get('group')!=group:continue
            url=source.get('url');domain=source.get('domain')
            if (source.get('identity_status')!='indexed' or source.get('review_required')
                    or not _publisher_url(url,domain)):
                pending.append(source);continue
            name=escape(source['name']);kind=kinds.get(source.get('kind'),'Publicación')
            market=source.get('market')
            detail=' · '.join(escape(str(v)) for v in (kind,market) if v)
            entries.append(f'<li><a href="{escape(url,quote=True)}" rel="noopener">{name}</a><span>{detail}</span></li>')
        if entries:
            groups.append(f'<details class="source-group"><summary>{escape(label)} <span>({len(entries)})</span></summary><ul>{"".join(entries)}</ul></details>')
    if pending:
        names=''.join(f'<li>{escape(s["name"])} <span>Por confirmar</span></li>' for s in pending)
        groups.append(f'<details class="source-group"><summary>Fuentes en revisión ({len(pending)})</summary><ul>{names}</ul></details>')
    if not groups:return ''
    return ('<section aria-labelledby="fuentes-negocios"><h2 id="fuentes-negocios">Fuentes de negocios y tecnología</h2>'
            '<p>Medios, portales institucionales y revistas para consultar en su sitio de origen. '
            'La portada reúne noticias de las últimas 24 horas; los estudios y las publicaciones de menor frecuencia '
            'pueden consultarse en sus editores. Los títulos completos y contenidos pertenecen a cada publicación.</p>'
            +''.join(groups)+'</section>')
