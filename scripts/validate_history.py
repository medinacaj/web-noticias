import json
from pathlib import Path

p = Path('data/historial.json')
d = json.loads(p.read_text(encoding='utf8'))
assert isinstance(d.get('noticias'), list)
for i, n in enumerate(d['noticias']):
    assert n.get('title') and n.get('link') and n.get('sources'), i
print('Historial validado:', len(d['noticias']))
