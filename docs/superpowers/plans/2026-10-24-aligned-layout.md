# Aligned Layout Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans in this session.

**Goal:** Alinear todas las bandas y compactar la cabecera sin perder controles.
**Architecture:** Corregir la cuadrícula compartida y los overrides de cabecera; no rediseñar componentes ni introducir dependencias.
**Tech Stack:** CSS/HTML existentes y Chromium.
**Spec:** docs/superpowers/specs/2026-10-24-aligned-layout-design.md

## Global Constraints
- Checkout existente, rama fix/grilla-cabecera-contenido desde origin/main.
- Mismas guías de contenido en cabecera, franja, main, boletín y pie.
- Sin cambios de paleta, fuentes, historial, privacidad o workflows.
- Mantener fecha/contador, lateral, autoplay, búsqueda y favoritos.

## Review Focus
- 1024 px con lateral abierto: no desborde ni solapamiento de controles.
- Pantallas de 1920/2560 px: todas las bandas se centran juntas.
- 320 px: cabecera <=80 px, fecha visible y controles táctiles útiles.
- Plegar el lateral y pasar a móvil conserva estado y coordenadas correctas.
- Menú fuera de la columna de contenido sigue siendo pulsable y accesible.

### Task 1: Corrección
- [ ] Pruebas geométricas RED para ancho compartido y altura compacta.
- [ ] Implementar límites y offsets compartidos; verificar GREEN y capturas.
- [ ] Suite, navegador y QA; revisión independiente de la corrección.

### Task 2: Publicar
- [ ] Issue, PR y CI para el SHA exacto; fusionar y verificar despliegue.
