"""Filtros de presentación sobre metadatos existentes, sin inferir hechos nuevos."""
import re
from scripts.editorial_signals import fold

CHOICES = {
    'nacional': [('nacional','Nacional'),('politica','Política'),('regiones','Regiones')],
    'tecnologia': [('tecnologia','Ciencia y tecnología'),('salud-ciencia','Salud'),('medioambiente','Medioambiente')],
    'economia': [('startups','Startups e inversión'),('empleo','Empleo'),('finanzas','Finanzas')],
    'cine-streaming': [('cine','En cines de Chile'),('streaming','Streaming en Chile'),('anuncios','Noticias de estrenos'),('guias','Guías')],
}
ECONOMY = {
    'startups': r'\b(startups?|venture capital|capital de riesgo|rondas? de inversion|capital semilla|fintech|scaleups?)\b',
    'empleo': r'\b(empleo|empleos|laboral|trabajadores|sueldos|salarios|contratacion|desempleo)\b',
    'finanzas': r'\b(bancos?|bancario|dolar|inflacion|tasas? de interes|bolsa|creditos?|pensiones)\b',
}


def story_topics(story):
    category = story.get('category', '')
    result = [category]
    if category == 'economia':
        title = fold(story.get('title', ''))
        result.extend(key for key, pattern in ECONOMY.items() if re.search(pattern, title))
    kind = story.get('content_kind')
    if category == 'cine-streaming':
        if kind == 'premiere' and story.get('region') == 'CL':
            result.append('cine' if story.get('format') == 'Cine' else 'streaming')
        elif kind == 'premiere-news':
            result.append('anuncios')
        elif kind == 'guide':
            result.append('guias')
    return result


def topic_choices(stories, section):
    available = {key for story in stories for key in story_topics(story)}
    choices = [(key,label) for key,label in CHOICES.get(section, []) if key in available]
    # Los filtros temáticos de negocios incluyen además noticias sin etiqueta.
    return [('', 'Todos')] + choices if len(choices) > 1 or (choices and section == 'economia') else []
