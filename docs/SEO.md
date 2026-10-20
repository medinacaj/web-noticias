# SEO técnico y transparencia — Noticias del Momento

**Tipo de proyecto:** portal de agregación estático (GitHub Pages), no sitio que publica artículos originales de terceros. Jurisdicción principal de uso prevista: Chile; los editores enlazados pueden pertenecer a otros países.

## Inventario verificable

| Recurso | Comportamiento en código |
| --- | --- |
| `/` | Portada actualizada y renderizada en HTML; `canonical` propia, `WebSite` + `CollectionPage` e `ItemList` de enlaces **externos**. |
| `/sobre-el-portal.html` | Página permanente propia, indexable, con explicación del proceso y atribución; `AboutPage`. |
| `/sitemap.xml` | Contiene únicamente las dos páginas propias indexables: portada y sobre el portal. No incluye artículos ajenos ni páginas `noindex`. |
| `/boletin-diario.html` | Vista previa temporal con `noindex`: no se presenta como página editorial permanente y **no envía correos**. |
| `/404.html` | Página de error con `noindex`. |
| `/robots.txt` | Archivo informativo con URL de sitemap. **En GitHub Pages con ruta de proyecto** no está en la raíz del host: los buscadores normalmente consultan `https://medinacaj.github.io/robots.txt`, fuera del ámbito de este repositorio. No atribuirle efecto de control de rastreo. |
| Imágenes | Enlaces a fotografías de medios; carga diferida para secundarias y prioridad alta para imagen principal. El tiempo real depende de los servidores de terceros. |
| Fonts | Google Fonts con `preconnect` y `display=swap`; dependencia externa a medir con datos de usuario real. |

No generar `NewsArticle` como si esta web fuese la autora o editora del contenido de cada medio. Los titulares continúan enlazando a los artículos originales. La selección automática **no es verificación de hechos independiente**.

## Verificaciones sin red

```bash
python3 -m unittest discover -s tests -v
python3 fetch_noticias.py --solo-render
python3 scripts/audit_seo.py --site public
```

También se ejecuta el QA visual existente con Chromium en 320, 375, 768, 1024 y 1440 píxeles. Un test en verde verifica que el HTML se genera correctamente, **no** que Google haya indexado páginas ni que las Core Web Vitals sean buenas en usuarios reales.

## Activación y medición en Google Search Console

1. Verificar una propiedad de prefijo URL que coincida con la URL pública real, por ejemplo `https://medinacaj.github.io/web-noticias/`. Para el método de etiqueta HTML, configurar la variable no secreta `GSC_VERIFICATION` en GitHub Actions (el workflow ya la lee). Revisar la propiedad y la etiqueta realmente publicada antes de dar por validada la verificación.
2. Enviar como sitemap `https://medinacaj.github.io/web-noticias/sitemap.xml` y comprobar que Google puede leerlo. Un sitemap **sugiere** URLs; no obliga a indexarlas ni garantiza tráfico.
3. Inspeccionar tanto `/` como `/sobre-el-portal.html` (URL Inspection). Revisar canónica elegida, rastreo, estado de indexación, cobertura y mejoras detectadas. Conservar la vista previa del boletín fuera del índice.
4. Usar PageSpeed Insights y las Core Web Vitals de Search Console para comprobar **LCP inferior a 2,5 s, INP inferior a 200 ms y CLS inferior a 0,1**, preferentemente en datos reales de móvil. Si no hay muestra suficiente, registrar «datos insuficientes» y no inventar una puntuación.
5. Medir consultas, impresiones, CTR y cobertura a lo largo de las semanas. No confundir clics a los medios originales con visitas orgánicas de Google a esta web.

Si se adopta dominio propio, actualizar `SITE_URL` y verificar **todas** las URL canónicas y enlaces de sitemap antes de publicar. Un robots.txt de raíz de dominio requiere control real del host raíz.

## Límites, riesgos y responsabilidad

- No existe evidencia de que las páginas ya estén indexadas o de posiciones/visitas reales; requiere Search Console.
- No se han verificado permisos de reutilización de cada fuente, fotografía o descripción; respetar las licencias, atribución, condiciones de uso y rectificaciones aplicables. No copiar artículos completos.
- Google puede decidir no indexar páginas basadas principalmente en enlaces agregados. El contenido informativo original y útil, la experiencia real y la calidad editorial importan más que metadatos aislados.
- El CDN de fotografías y las fuentes externas pueden afectar LCP y estabilidad. No replicar fotografías en infraestructura propia sin una evaluación de derechos.
- No agregar anuncios, analíticas invasivas, servicios de pago o formularios que recopilen datos personales como parte de una optimización SEO.

**Referencias técnicas oficiales:**
- https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap
- https://developers.google.com/search/docs/crawling-indexing/robots/intro
- https://developers.google.com/search/docs/appearance/structured-data/article
- https://developers.google.com/search/docs/appearance/core-web-vitals
