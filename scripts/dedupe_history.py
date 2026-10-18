import json
from pathlib import Path
from urllib.parse import urlsplit
p=Path('data/historial.json')
d=json.loads(p.read_text(encoding='utf8'))
seen=set();out=[]
for n in d['noticias']:
    u=urlsplit(n['link']);k=(u.netloc.lower(),u.path.rstrip('/'))
    if k in seen: continue
    seen.add(k);out.append(n)
if len(out)!=len(d['noticias']):
    print('Duplicados eliminados:',len(d['noticias'])-len(out))
    d['noticias']=out
    p.write_text(json.dumps(d,ensure_ascii=False,indent=1)+'\n',encoding='utf8')
