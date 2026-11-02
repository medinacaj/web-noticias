"""Group displayed sections without changing ingestion or story categories."""

# Los rótulos salen de CATEGORIES: menú, sección, tarjetas y filtros usan el mismo nombre.
PRESENTATION_LABELS = {"nacional": "Chile", "internacional": "Mundo"}

# Cambia la presentación, nunca el registro editorial original.
_DESTINATIONS = {"politica": "nacional", "regiones": "nacional",
                 "salud-ciencia": "tecnologia", "medioambiente": "tecnologia"}


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
    each source list's relevance order, reserving up to four places per
    subtopic before filling remaining places from the destination.
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
        seen = {id(item) for item in primary}
        pools = []
        for origin, parent in _DESTINATIONS.items():
            if parent != destination:
                continue
            pool = _unique(by_category.get(origin, []), seen)
            seen.update(id(item) for item in pool)
            pools.append(pool)
        counts = [0] * len(pools)
        budget = max(0, limit - bool(primary))
        for index in range(4):
            for slot, pool in enumerate(pools):
                if budget and len(pool) > index:
                    counts[slot] += 1
                    budget -= 1
        selected = primary[:max(0, limit - sum(counts))]
        for pool, count in zip(pools, counts):
            selected.extend(pool[:count])
        for pool, count in zip(pools, counts):
            selected.extend(pool[count:count + max(0, limit - len(selected))])
        grouped[destination] = selected
    return grouped
