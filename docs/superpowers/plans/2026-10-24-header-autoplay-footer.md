# Header, Autoplay and Footer Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans; implementar en esta sesión.

**Goal:** Aplicar los ajustes de fecha, contador, avance automático y pie solicitados.
**Architecture:** Conservar el generador y componentes; un contador derivado de la selección publicada, tokens/markup de cabecera/pie y ciclo de reproducción dentro del controlador existente.
**Tech Stack:** Python, HTML/CSS/JS sin dependencias; Chromium.
**Spec:** docs/superpowers/specs/2026-10-24-header-autoplay-footer-design.md

## Global Constraints
- Rama fix/actualizacion-carrusel-pie desde origin/main en el checkout aislado existente.
- Sin cambios de fuentes, historial, workflows, permisos o paleta.
- Mantener navegación lateral, búsqueda, favoritos, Agenda, firma y enlaces de privacidad.

## Review Focus
- Conteo real de URLs distintas tras agrupar secciones; no usar el total previo del historial.
- Temporizador único, cancelado al pausar/ocultarse; no autoanuncios aria-live.
- Movimiento reducido, puntero y teclado no impiden la reanudación explícita.
- Cabecera legible y pie compacto sin desbordes en móvil.
- Sin noticias/una noticia y enlaces comerciales opcionales.

### Task 1: Conteo, cabecera y pie
- [ ] RED: contador derivado de selección, fecha a la derecha y pie sin los bloques marcados.
- [ ] Implementar render_edition_count(sel), markup y estilos compactos; conservar sección y privacidad.
- [ ] GREEN: suite, pruebas de navegador, SEO y capturas.

### Task 2: Avance automático
- [ ] RED: probar avance real, pausa/reanudación y preferencia de movimiento reducido.
- [ ] Implementar temporizador de 6000 ms con pausas y control accesible.
- [ ] GREEN y QA responsive; revisión independiente.

### Task 3: Publicar
- [ ] Commit/PR, CI aprobada para SHA exacto, fusión y verificación de despliegue.
