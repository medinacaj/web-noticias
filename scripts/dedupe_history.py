"""Normalización determinista de historial de noticias, sin consultar Internet."""
import json
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit


def canonical_key(link):
    """Las variantes de tracking de la misma URL corresponden a una noticia."""
    u = urlsplit(link)
    if u.scheme not in ("http", "https") or not u.netloc:
        raise ValueError("Enlace no válido")
    tracking = {"oc", "gclid", "fbclid", "msclkid", "mc_cid", "mc_eid", "_ga", "igshid"}
    query = tuple((key, value) for key, value in parse_qsl(u.query, keep_blank_values=True)
                  if not key.casefold().startswith("utm_") and key.casefold() not in tracking)
    return u.netloc.lower(), u.path.rstrip("/") or "/", query


def deduplicate(items):
    seen = {}
    result = []
    for news in items:
        key = canonical_key(news["link"])
        if key in seen:
            target = result[seen[key]]
            merged = list(dict.fromkeys(
                list(target.get("sources") or []) + list(news.get("sources") or [])
            ))
            if merged:
                target["sources"] = merged
            # No perder contexto editorial al consolidar dos enlaces iguales.
            for field in ("summary", "image", "source_url", "image_checked_at"):
                if not target.get(field) and news.get(field):
                    target[field] = news[field]
            for field in ("publisher_id", "source_country", "source_country_label"):
                if not target.get(field) and news.get(field):
                    target[field] = news[field]
            if target.get("metadata_only") or news.get("metadata_only"):
                target["metadata_only"] = True
                target["summary"] = ""
                target["image"] = ""
            coverage = list(target.get("coverages") or [])
            covered_links = {item.get("link") for item in coverage if isinstance(item, dict)}
            for item in news.get("coverages") or []:
                if isinstance(item, dict) and item.get("link") and item["link"] not in covered_links:
                    coverage.append(item)
                    covered_links.add(item["link"])
            if coverage:
                target["coverages"] = coverage[:12]
            for field in ("published", "first_seen"):
                if news.get(field) and (not target.get(field) or news[field] < target[field]):
                    target[field] = news[field]
            continue
        seen[key] = len(result)
        entry = dict(news)
        if entry.get("metadata_only"):
            entry["summary"] = ""
            entry["image"] = ""
        result.append(entry)
    return result


def main():
    p = Path("data/historial.json")
    raw = p.read_text(encoding="utf8")
    data = json.loads(raw)
    original = data["noticias"]
    cleaned = deduplicate(original)
    removed = len(original) - len(cleaned)
    if removed:
        data["noticias"] = cleaned
        p.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    print(f"Noticias: {len(cleaned)}; enlaces duplicados eliminados: {removed}")


if __name__ == "__main__":
    main()

