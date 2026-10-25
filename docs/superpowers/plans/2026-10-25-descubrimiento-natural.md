# Descubrimiento y retorno natural

Objetivo aprobado por el usuario: mejorar variedad, novedades desde la visita anterior y acceso a contexto/preferencias; sin nuevos bloques.

Arquitectura: selección Python conserva fuentes y relevancia; JS independiente consume first_seen y la fecha de edición existente. Un solo valor local guarda la última edición, sin URLs vistas ni clics. HTML funciona sin JS.

- [x] Probar selección de destacadas variadas dentro de los doce candidatos recientes mejor clasificados, sin vaciar categorías ni mutar candidatos; rellenar si faltan alternativas.
- [x] Exponer fecha de incorporación y clave canónica en enlaces de tarjetas; no confundir con publicación.
- [x] Probar primera visita, retorno, recarga, almacenamiento bloqueado/corrupto, edición antigua y límites temporales. Contar solo URLs únicas presentes y compatibles con filtros.
- [x] Integrar contador opcional en título Destacadas y etiqueta Nueva junto a los metadatos; al tocar ir a una novedad y revelar Ver más si hace falta. No mover automáticamente contenido.
- [x] Renombrar Comparar a Otras coberturas, pulir etiquetas de preferencias, permitir volver a todas las noticias con un control de texto dentro del panel existente.
- [x] Verificar suite, Chromium, siete anchos y capturas con novedades visibles; revisión independiente.
- [ ] CI exacto y publicación; resultado en Issue/PR.

Restricciones: sin nuevas fuentes, sin perfiles inferidos, sin peticiones de red adicionales ni analítica, conservar carrusel y guías. Última edición local se conserva solo para comparar incorporaciones en ese navegador; una edición antigua no rebaja la marca. Relevancia no se sustituye por cuotas geográficas inventadas. El número de medios no equivale a popularidad ni verificación.
