# Preparación de Google AdSense

El módulo `scripts/adsense.py` prepara la verificación y una futura carga de Auto Ads. No crea una cuenta, solicita aprobación ni demuestra cumplimiento. Por defecto no publica etiquetas de AdSense, scripts ni `ads.txt`. No se han configurado credenciales o identificadores reales.

## URL y alojamiento actuales

El portal conserva `https://medinacaj.github.io/web-noticias/` en GitHub Pages. Esa subruta no administra `https://medinacaj.github.io/ads.txt`; el generador mantiene la publicidad desactivada incluso si se declara `ADSENSE_READY=true`. No cambiar `SITE_URL`, crear otro repositorio, contratar un servicio ni migrar el portal para completar esta preparación.

Google describe `ads.txt` como **recomendado, no obligatorio**. El requisito de raíz administrable es un control deliberadamente más restrictivo de este proyecto. El módulo comprueba el formato y una declaración explícita del responsable; no prueba propiedad ni acceso real al servidor. [Guía oficial de ads.txt](https://support.google.com/adsense/answer/12171612?hl=en).

Un eventual sitio de usuario `https://medinacaj.github.io/` podría alojar ese archivo si el responsable controla su raíz. `github.io` figura en la [Public Suffix List](https://publicsuffix.org/list/public_suffix_list.dat), y Google permite presentar subdominios de esas plataformas. Esa posibilidad no garantiza admisión ni autoriza mover el portal. [Tipos de sitio admitidos](https://support.google.com/adsense/answer/12170421?hl=en).

## Configuración explícita

| Variable | Función |
| --- | --- |
| `ADSENSE_PUBLISHER_ID` | ID real obtenido en la cuenta: prefijo `ca-pub-` y exactamente 16 dígitos ASCII. No copiar el ID de una guía o de las pruebas. Los dos IDs publicados como ejemplos en la documentación de Google se rechazan. |
| `ADSENSE_READY` | Sólo `true` solicita cargar publicidad. Dejar vacío o `false` mientras falten aprobación, privacidad o revisión de consentimiento. |
| `ADSENSE_PRIVACY_URL` | URL HTTPS real, pública y revisada de la política aplicable a publicidad. |
| `ADSENSE_ROOT_CONTROLLED` | Sólo `true` después de comprobar control y publicación efectiva del sitio y de `ads.txt` en la raíz del host. No activarlo en la subruta actual. |
| `SITE_URL` | URL pública efectiva del portal. Esta preparación conserva la actual. |

Un ID válido puede producir únicamente la metaetiqueta de propiedad aunque `ADSENSE_READY` esté desactivado. La metaetiqueta no ejecuta el script de anuncios. La [conexión oficial](https://support.google.com/adsense/answer/7584263?hl=en) admite verificación por meta y requiere que Google apruebe el sitio antes de mostrar anuncios. El formato del ID no permite comprobar que pertenece al responsable: esa verificación sigue pendiente.

El script se devuelve sólo con todos los campos requeridos, raíz HTTPS sin subruta, credenciales, puerto, consulta o fragmento y declaración explícita de control. Se rechazan hosts locales/IP y raíces GitHub Pages que no sean de usuario. El código no implementa un catálogo completo de sufijos públicos ni verifica el estado de la cuenta.

`ads.txt` se prepara con ID válido y raíz controlada, incluso durante la etapa de verificación con anuncios desactivados. Publica la directiva `DIRECT` sólo si corresponde realmente a la relación con Google; contrastar la línea con la obtenida de la cuenta. No confundir generar el archivo con haberlo desplegado ni con el estado «Authorized» de AdSense.

## Integración en el generador

```python
from scripts.adsense import configured_adsense
adsense = configured_adsense(os.environ, SITE_URL)
```

Reemplazar `%%ADSENSE_META%%` por `adsense["meta"]` y `%%ADSENSE_SCRIPT%%` por `adsense["script"]` dentro de `<head>`. `%%ADSENSE_PRIVACY_LINK%%` corresponde a `adsense["footer"]` en el pie. Los fragmentos ya están escapados y sólo la portada debe cargar el script; no añadirlo a la vista de boletín, 404 ni páginas vacías.

Después de copiar los estáticos, escribir `ads.txt` únicamente si `adsense["ads_txt"]` no está vacío. Eliminar un `ads.txt` residual del directorio de salida cuando la configuración deje de permitirlo. Mantener vacíos todos los marcadores al faltar configuración. El módulo no cambia archivos, hace solicitudes ni modifica variables del entorno. Pasar `{}` permite validar el estado desactivado sin heredar la configuración de la máquina.

## Revisión antes de una futura activación

El responsable debe comprobar la cuenta y aprobación de Google, identidad/contacto reales, control del host, respuesta HTTPS de la política y de `ads.txt`, derechos editoriales y configuración de Auto Ads. La documentación no es una política pública de privacidad y no crea una identidad de responsable.

Google limita publicidad sobre contenido replicado sin valor añadido y exige explicar los tratamientos de datos y tecnologías de terceros. La agrupación de titulares y enlaces no acredita aprobación ni licencia para monetizar contenido o imágenes. [Políticas de Editores](https://support.google.com/publisherpolicies/answer/10502938?hl=en).

Audiencia principal prevista: Chile; los territorios efectivos de lectores no están acreditados. Antes de cargar publicidad, determinar los requisitos aplicables a esa audiencia y verificar una solución de consentimiento cuando corresponda. Para anuncios personalizados a lectores del EEE, Reino Unido y Suiza, Google exige una CMP certificada con TCF. Esta preparación no implementa una CMP ni certifica cumplimiento normativo. [Requisitos de consentimiento de Google](https://support.google.com/adsense/answer/13554116?hl=en).

| Riesgo | Control y prueba | Responsable y estado |
| --- | --- | --- |
| Carga accidental de terceros | Gates explícitos y pruebas negativas por cada valor ausente o inválido | Mantenedor: automatizado; activación pendiente del responsable |
| Suponer control de raíz por tener una URL | Subruta bloqueada y declaración separada de control | Responsable: verificación de hosting pendiente |
| Identidad, privacidad, licencia o consentimiento inventados | No generar una política de ejemplo ni datos de contacto | Responsable: revisión documental y operativa pendiente |
| Agregación insuficiente para monetizar | Revisar derechos, curación y aportación editorial real | Responsable/editor: admisión de Google no verificada |

Fuentes oficiales consultadas el 23 de octubre de 2026. Las URLs se validan por formato; estas pruebas no certifican disponibilidad, contenido o aprobación.

## Verificación técnica

```bash
python3 -m unittest discover -s tests -v
python3 fetch_noticias.py --solo-render
python3 scripts/audit_seo.py --site public
```

Revisar que, sin configuración, el HTML no contiene solicitudes de Google Ads, IDs de ejemplo, marcadores pendientes ni bloques publicitarios vacíos. La activación real exige una prueba del despliegue y de las opciones móviles, densidad y formatos de Auto Ads. Los cambios de privacidad y workflows se revisan conforme a `docs/agent-workflow.md`.
