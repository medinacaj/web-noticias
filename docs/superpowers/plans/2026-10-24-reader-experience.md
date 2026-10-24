# Reader Experience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reducir ruido de navegación y diversificar Cultura sin perder capacidades existentes.
**Architecture:** Generación Python existente, HTML/CSS en template.html y controles de lectura en un pequeño static/reader-ui.js. PR96 forma la base de la rama; no hay cambios de framework.
**Tech Stack:** Python 3.12, HTML/CSS, JavaScript sin dependencias; Chromium/Playwright para verificación.
**Spec:** docs/superpowers/specs/2026-10-24-reader-experience-design.md

## Global Constraints
- No editar data/historial.json ni publicar fixtures.
- Usar checkout aislado existente y rama feat/experiencia-noticias; no crear worktrees.
- Conservar metadatos SEO, atribución, paleta, búsqueda, favoritos y Agenda.
- No afirmar permisos de fuentes, perfil LinkedIn, CI remota o fusión sin evidencia.

## Review Focus
- LocalStorage bloqueado: controles funcionan sin persistencia.
- Cambio de tamaño: menú móvil no reemplaza la elección de escritorio.
- Cambios del sistema: tema automático reacciona; elección manual prevalece.
- Pocas noticias, enlaces repetidos o fecha ausente: no inventar tarjetas ni actualidad.
- Fuente de entretenimiento caída: el resto de la recolección continúa; sin GNews adicional.

### Task 1: Navegación y composición
**Files:** template.html, static/reader-ui.js, fetch_noticias.py; tests/test_reader_experience.py, tests/reader_ui_browser.py; actualizar test_navigation_polish.py y test_card_contrast.py para requisitos nuevos.
**Interfaces:** select(stories, now) añade latest; render_breaking(sel, now) produce carrusel de enlaces. JS consume #menu-toggle, #site-nav, #theme-select, #theme-toggle y [data-carousel].
- [x] Añadir pruebas de titulares distintos/orden/faltantes y navegador para menú, tema, firma, carrusel y overflow.
- [x] Ejecutarlas y comprobar que fallan por comportamiento ausente.
- [x] Implementar cabecera compacta, barra lateral, tema, carrusel, detalles del pie, firma y fallback tipográfico.
- [x] Ejecutar suite y navegador; corregir regresiones y revisar capturas.
- [ ] Commit de la UI validada.

### Task 2: Cultura internacional
**Files:** scripts/entertainment.py, fetch_noticias.py, tests/test_entertainment.py, docs/FUENTES_ENTRETENIMIENTO.md.
**Interfaces:** collect_entertainment(now, fetch=None) devuelve entradas category=cultura, metadata_only=True, sin summary/image, con fecha original válida.
- [x] Probar ediciones en español fuera de Chile, límites, dominios/fechas inválidas, fallo independiente y conexión con collect().
- [x] Verificar RED y luego implementar consultas acotadas a ediciones ES/MX/US en español, reutilizando RSS existente.
- [x] Verificar GREEN, suite completa, pruebas de eventos, render, SEO y navegador.
- [x] Documentar evidencia y límites; commit.

### Task 3: Entrega
- [ ] Revisión independiente del diff y verificación final del estado y cambios.
- [ ] Intentar operación GitHub solo por rutas autorizadas; si API bloqueada, guardar adición api.github.com en borrador e informar acción necesaria.
- [ ] Entregar cambios verificables y limitaciones, distinguiendo incorporación local del PR96 y fusión/publicación remota.
