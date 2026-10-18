import json
from datetime import datetime
from pathlib import Path
from dedupe_history import canonical_key

data=json.loads(Path("data/historial.json").read_text(encoding="utf8"))
assert isinstance(data.get("noticias"),list), "Falta noticias[]"
seen=set()
for i,item in enumerate(data["noticias"]):
    assert isinstance(item,dict), (i,"objeto inválido")
    assert isinstance(item.get("title"),str) and len(item["title"].strip())>5, (i,"título")
    assert isinstance(item.get("category"),str) and item["category"], (i,"categoría")
    assert isinstance(item.get("sources"),list) and all(isinstance(x,str) and x.strip() for x in item["sources"]) and item["sources"], (i,"medios")
    key=canonical_key(item.get("link",""))
    assert key not in seen, (i,"URL duplicada")
    seen.add(key)
    for field in ("published","first_seen"):
        if item.get(field):
            date=datetime.fromisoformat(item[field].replace("Z","+00:00"))
            assert date.tzinfo is not None, (i,field)
print("Historial validado:",len(data["noticias"]))
