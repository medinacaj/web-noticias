"""Group displayed sections without changing ingestion or story categories."""

# Los rótulos salen de CATEGORIES: menú, sección, tarjetas y filtros usan el mismo nombre.
PRESENTATION_LABELS = {}

# Salud se publica dentro de «Ciencia y tecnología»; Medioambiente tiene sección propia.
_DESTINATIONS = {"salud-ciencia": "tecnologia"}
_SUBTOPICS = {destination: origin for origin, destination in _DESTINATIONS.items()}


def canonical_section(category):
    """Return the display section/anchor; keep the story's category intact."""
    return _DESTINATIONS.get(category, category)


def _unique(items, seen=None):
    """Keep original object references and order, omitting repeated objects."""
    seen = set() if seen is None else set(seen)
    result = []
    for item in items:
        identity = id(item)
        if identity not in seen:
            seen.add(identity)
            result.append(item)
    return result


def group_sections(by_category, limit=24):
    """Return new ordered lists with up to ``limit`` stories per section.

    A group's position is its first member's position in the input. Preserve
    each source list's relevance order, reserving up to four places for its
    smaller subtopic before filling remaining places from the destination.
    Any leftover room is filled with additional subtopic stories. Equal but
    distinct records remain distinct; ingestion owns article deduplication.
    """
    limit = max(0, limit)
    grouped = {}
    for category in by_category:
        destination = canonical_section(category)
        if destination in grouped:
            continue
        primary = _unique(by_category.get(destination, []))
        subtopic = _unique(by_category.get(_SUBTOPICS.get(destination), []),
                           {id(item) for item in primary})
        reserved = min(4, len(subtopic), limit)
        selected_primary = primary[:limit - reserved]
        grouped[destination] = (selected_primary +
                                subtopic[:limit - len(selected_primary)])
    return grouped
