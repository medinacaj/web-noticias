# Noticias del Momento

Web Noticias es un agregador estático de noticias de Chile, Latinoamérica y el mundo. Presenta titulares con atribución y enlaces a los medios originales, una Agenda de eventos y una sección de Cine y streaming. La disponibilidad y precisión de las noticias dependen de las fuentes externas y requieren revisión editorial. [Sitio público](https://medinacaj.github.io/web-noticias/) · [Repositorio oficial](https://github.com/medinacaj/web-noticias)

## Arquitectura

- `fetch_noticias.py` reúne noticias de Google Noticias RSS, fuentes habilitadas y GNews cuando está configurado. Selecciona noticias y genera HTML estático a partir de `template.html`. GitHub Actions genera el sitio y GitHub Pages sirve la salida de `public/`. JavaScript y CSS nativos completan la experiencia de lectura.
- `static/reader-ui.js`, `static/edition-status.js` y `static/visit-updates.js` atienden la lectura y el estado de la edición. `scripts/presentation_groups.py` y `scripts/reading_topics.py` organizan secciones y filtros. `scripts/discovery.py` genera Hoy y Temas, con estilos y preferencias compartidos en `static/reading-pages.*`.
- `scripts/culture_content.py`, `scripts/premiere_catalog.py`, `scripts/premiere_news.py` y `scripts/weekly_releases.py` organizan Cine y streaming. [Fuentes de entretenimiento](docs/FUENTES_ENTRETENIMIENTO.md)
- `eventos/` recolecta eventos públicos y `scripts/agenda.py` presenta los aptos para Agenda. Los snapshots operativos están en `events-data`; el historial de noticias, en `news-data`. El `data/historial.json` de la rama de código se usa como fixture o bootstrap. [Recolector](eventos/README.md) · [Separación de código y datos](docs/main-protection.md)

## Desarrollo local

Desde la raíz del checkout, con Python 3.12 y con Node y `jq` disponibles en `PATH` para las pruebas de JavaScript y del monitor:

```bash
python3.12 -m venv /tmp/web-noticias-venv
source /tmp/web-noticias-venv/bin/activate
python -m pip install gnews-decoder==0.1.1
SITE_URL=https://medinacaj.github.io/web-noticias/ python scripts/render_visual_fixture.py
python -m http.server 8765 --bind 127.0.0.1 --directory public
```

El render de prueba utiliza un reloj fijo derivado del fixture y genera la portada en `public/index.html`, entre otras páginas. El servidor sirve la salida por HTTP local. La validación de contenido puede ejecutarse en otra terminal con el mismo entorno virtual.

```bash
python -m unittest discover -s tests -q
(cd eventos && python -m unittest discover -s tests -t . -q)
python scripts/validate_history.py
python scripts/audit_editorial_quality.py --strict
python scripts/audit_seo.py --site public
```

Para revisar interacciones, instala `playwright==1.56.0` en el mismo entorno. En Linux, la suite `PYTHONPATH=. python tests/reader_ui_browser.py` usa Chromium en `/usr/bin/chromium` y el sitio ya generado. El workflow de QA visual instala su propio Chromium. El proceso de producción y sus variables se describen en la memoria. [Workflow de QA visual](.github/workflows/visual-qa.yml) · [Memoria operativa](docs/MEMORIA_OPERATIVA.md)

## Continuidad

Consulta la rama predeterminada efectiva, el SHA, sus PR y la CI asociada. Verifica la URL pública cuando corresponda y registra la evidencia disponible por separado. Mantén secretos y datos de lectores fuera de las pruebas y de los respaldos. [Reglas del repositorio](AGENTS.md) · [Decisiones](docs/DECISIONES.md) · [Cambios](CHANGELOG.md) · [Instrucción para una nueva sesión](docs/CONTINUIDAD_NUEVA_SESION.md) · [Seguimiento de auditoría #256](https://github.com/medinacaj/web-noticias/issues/256)
