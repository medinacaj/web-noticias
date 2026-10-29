"""Categorías de entretenimiento: tarjetas comunes, independientes de la ingesta factual."""
from scripts.dedupe_history import canonical_key

CINEMA_SECTION={'key':'cine-streaming','label':'Cine y streaming'}


def section_categories(categories):
    """Categoría de presentación, sin incorporar consultas de ingesta."""
    result=[]
    for category in categories:
        result.append(category)
        if category['key']=='cultura':result.append(CINEMA_SECTION)
    if not any(c['key']==CINEMA_SECTION['key'] for c in result):result.append(CINEMA_SECTION)
    return result


def add_culture_content(by_category,now,*,satire_items=None,release_guides=None,existing=()):
    from scripts.satire import validated_items, SOURCE_NAME, SOURCE_URL
    from scripts.weekly_releases import current_guides
    from scripts.global_sources import load_catalog as world
    from scripts.regional_sources import load_catalog as regional
    from scripts.latam import catalog_allowed

    result={key:list(stories) for key,stories in by_category.items()}
    published=list(existing)+[s for items in result.values() for s in items]
    seen={canonical_key(s['link']) for s in published}
    additions=[]
    if satire_items is not None:
        valid=validated_items(satire_items,now)
        additions.extend({**s,'content_kind':'satire'} for s in valid)
        # La ficha del medio no es un artículo reciente ni recibe una fecha ficticia.
        if not valid and catalog_allowed({'source':SOURCE_NAME,'source_url':SOURCE_URL,
                                         'link':SOURCE_URL},world()+regional()):
            additions.append({'title':SOURCE_NAME,'source':SOURCE_NAME,'source_url':SOURCE_URL,
                              'link':SOURCE_URL,'content_kind':'satire-source','published':None,
                              'summary':'','image':'','metadata_only':True})
    additions.extend({**s,'content_kind':'guide','source_country_label':'Guía de '+s['market']}
                     for s in current_guides(release_guides or [],now))
    for item in additions:
        key=canonical_key(item['link'])
        if key in seen:continue
        seen.add(key)
        destination=CINEMA_SECTION['key'] if item['content_kind']=='guide' else 'cultura'
        result.setdefault(destination,[]).append({**item,'category':destination,
                   'sources':[item['source']],'first_seen':''})
    return result


def content_kind(story):
    kind=story.get('content_kind')
    return kind if kind in ('guide','satire','satire-source') else ''


def card_label(story):
    kind=content_kind(story)
    if kind=='guide':return 'Cine y streaming'
    if kind in ('satire','satire-source'):return 'Sátira y humor'
    return ''
