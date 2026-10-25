# Pulido de lectura

Objetivo autorizado por el usuario: fotografías oficiales, jerarquía, espacios y controles más claros conservando la alineación y la paleta.

Enfoque: ampliar el lector existente de metadatos con JSON-LD de artículos; conservar precedencia Open Graph y validación HTTPS. No consultar nuevas fuentes ni copiar fotografías. Mantener las tarjetas tipográficas cuando no hay imagen.

- [x] Probar extracción de imágenes de artículos, exclusión de logos, JSON inválido, URL privada y precedencia.
- [x] Añadir soporte acotado de metadatos estructurados.
- [x] Reducir separación entre secciones a 48 px / 32 px móvil, ajustar titular móvil y ancho de lectura; mostrar Buscar/Vista en escritorio amplio.
- [x] Verificar suites existentes, Chromium y siete anchos, revisar capturas claro/oscuro.
- [ ] PR, CI del SHA final, fusión y comprobación del despliegue.

Riesgos: no todos los editores ofrecen fotografías o permiten mostrarlas. No se garantiza cobertura fotográfica; conservar texto y atribución. Sin cambios de permisos, catálogos, licencias, dependencias ni workflows.
