# Contrast, Strip and Sidebar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Corregir la paleta azul, compactar «Lo último» y hacer visible el control lateral.
**Architecture:** Cambios acotados a tokens/CSS de template.html, markup de render_breaking() y controles existentes en reader-ui.js. Conservar la arquitectura y pruebas de lectura.
**Tech Stack:** Python 3.12, HTML/CSS/JS sin dependencias, Chromium/Playwright.
**Spec:** docs/superpowers/specs/2026-10-24-contrast-strip-sidebar-design.md

## Global Constraints
- Usar checkout existente en rama fix/contraste-franja-lateral desde origin/main; no crear worktrees.
- No cambiar historial, feeds, workflows ni permisos.
- Paleta, alturas y proporciones conforme al spec; contraste de texto >=4.5:1.
- Preservar modo automático/manual, búsqueda, favoritos, Agenda y lectura sin JS.

## Review Focus
- Flecha accesible tras plegar el panel, con reduced-motion y tras recargar.
- Menú móvil y su fondo se cierran conjuntamente sin cambiar la elección de escritorio.
- Titulares largos y tipografía ampliada no elevan la franja ni crean scroll horizontal de página.
- Cambio de tema o ancho conserva colores legibles y contador del carrusel correcto.
- Cero/una noticia no produce controles inútiles ni anuncios ficticios.

### Task 1: Franja y control lateral
**Files:** fetch_noticias.py, template.html, static/reader-ui.js, tests/reader_ui_browser.py.
**Interfaces:** render_breaking(sel, now) produce breaking-inner con track y controles en la misma fila. #sidebar-edge sincroniza con #menu-toggle y #site-nav.
- [x] Añadir pruebas reales de altura <=60 px, una noticia por paso y flecha plegar/reabrir/persistencia.
- [x] Ejecutar RED; implementar markup/estilos/controles mínimos y verificar GREEN.

### Task 2: Paleta y consistencia
**Files:** template.html, tests/test_card_contrast.py, tests/test_design_consistency.py y aserciones antiguas de tokens en tests; CLAUDE.md.
**Interfaces:** Tokens existentes con nuevos valores; todos los componentes siguen consumiendo esas variables.
- [x] Añadir verificaciones de neutralidad y contraste real en navegador y actualizar contratos de paleta solicitada; comprobar RED.
- [x] Aplicar la paleta en claro/oscuro, sombras suaves, detalles de logo, boletín/pie y controles.
- [ ] Suite completa, navegador, capturas, generación y SEO; revisión independiente del diff.

### Task 3: Publicación
- [ ] Issue, commit y PR con evidencia; CI del SHA final aprobada, sin bloqueos.
- [ ] Fusionar con SHA esperado y comprobar despliegue y monitor público. No entregar solo una rama pendiente.
