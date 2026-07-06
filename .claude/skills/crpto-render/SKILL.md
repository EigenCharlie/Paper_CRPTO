---
name: crpto-render
description: Renderiza el libro Quarto a HTML, abre el resultado y opcionalmente captura screenshots para QA visual.
---

# /crpto-render

Renderiza el libro CRPTO y valida el resultado.

## Pasos

1. **Render**:
   ```powershell
   uv run -- quarto render book --to html
   ```
   Captura tiempo de render y warnings.

2. **Verificación de salida**: confirmar que `book/_book/index.html` existe y que se generaron los 24 capítulos.

3. **QA visual** (si el usuario tiene Chrome MCP o Playwright MCP):
   - Abre `book/_book/index.html`.
   - Screenshot de:
     - Portada (`index.html`).
     - Tabla con `df-print: paged` (cualquier capítulo de resultados, e.g. `04-resultados.html`).
     - Callout custom (`.mini-abstract`, `.equation-card`).
     - Grid de chapter-cards.
     - Lightbox al hacer click en una figura.
     - Toggle dark mode (si activado).
   - Reporta cualquier anomalía visual.

4. **QA de contenido**:
   - `book/_book/search.json` no vacío (búsqueda funcional).
   - No hay 404s en links internos: `find book/_book -name "*.html" | xargs grep -l '404\\|not found'`.
   - Bibliografía renderizada en `references.html`.

5. **Resumen al usuario**: páginas generadas, tiempo total, warnings, archivos cambiados.

## Argumentos

- Sin argumentos: render HTML completo.
- `pdf`: ejecuta `uv run -- quarto render book --to pdf` también.
- `preview`: arranca `uv run -- quarto preview book` en background y reporta la URL local.

## Notas

- NO usa `QUARTO_PYTHON=.venv/bin/python` (es path Linux y rompe en Windows). `uv run --` resuelve el Python del venv cross-platform.
- Si Quarto no está en PATH: reportar al usuario y abortar. No intentar instalar Quarto desde aquí.
- Si hay errores de chunk Python, correr `just book-clean` (purga `book/_book`, `book/_freeze`, `book/.quarto`) y re-renderizar.
