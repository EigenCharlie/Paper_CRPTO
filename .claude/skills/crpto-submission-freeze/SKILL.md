---
name: crpto-submission-freeze
description: Checklist ejecutable del freeze de submission IJDS - gates de calidad, sincronía de claims, PDFs oficiales, QA de anonimato y límite de páginas. Correr antes de tagear o subir a ScholarOne.
---

# /crpto-submission-freeze

Implementa el checklist de freeze (ventana Ago 9-10 del roadmap
`paper/submission/IJDS_SUBMISSION_ROADMAP_2026-08-10.md`). Reporte final
GO/NO-GO por sección; cualquier NO-GO bloquea el freeze.

## Pasos

1. **Gates de calidad**:
   ```powershell
   just lint
   just smoke
   just validate-champion
   ```

2. **Sincronía de claims**: correr `/crpto-claim-sync`. Debe salir verde.

3. **PDFs frescos**:
   ```powershell
   just paper-submission-pdf
   ```
   y el PDF oficial (los PDFs están gitignored — se regeneran localmente):
   ```powershell
   cd paper/submission
   latexmk -pdf -gg -interaction=nonstopmode CRPTO_ijds_submission.tex
   ```
   Verificar en el log `Output written on CRPTO_ijds_submission.pdf`; el
   "up-to-date" sin runs de pdflatex NO cuenta como rebuild.

   Si `latexmk` falla en PowerShell por el wrapper de TinyTeX
   (`runscript.tlu` con valor `nil`), usar el fallback probado:

   ```powershell
   cd paper/submission
   pdflatex -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
   bibtex CRPTO_ijds_submission
   pdflatex -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
   pdflatex -interaction=nonstopmode -halt-on-error CRPTO_ijds_submission.tex
   ```

   El fallback cuenta como rebuild oficial si produce
   `CRPTO_ijds_submission.pdf` desde el `.tex` sincronizado y el log muestra
   `Output written`. Reparación opcional del wrapper TinyTeX:
   `tlmgr update --self --all`.

4. **Límite de páginas**: el body debe quedar en <= 25 páginas excluyendo
   referencias (política IJDS). Verificar el total y en qué página empieza la
   bibliografía:
   ```powershell
   uv run --with pypdf python -c "from pypdf import PdfReader; r = PdfReader('paper/submission/CRPTO_ijds_submission.pdf'); print(len(r.pages))"
   ```

5. **QA de anonimato** (double-anonymous, dblanonrev): buscar en
   `CRPTO_ijds_submission.tex`, `CRPTO_ijds.qmd`, `supplement_ijds.qmd` y en el
   texto del PDF. Cero ocurrencias permitidas de:
   - nombres/correos del autor (`Vergara`, `cavr94`)
   - remotes propios (`EigenCharlie`, `github.com/EigenCharlie`, `dagshub.com/`)
   - paths locales (`C:\Users`, `C:/Users`, `/home/`)
   - `\AUTHOR{...}` no vacío o acknowledgements en el body

6. **Checklist de venue**: repasar `paper/submission/SCHOLARONE_FINAL_CHECKLIST.md`
   punto por punto y reportar los que queden pendientes (cover letter,
   disclosure form, title page no anónima van por separado, NO dentro del
   packet anónimo).

7. **Reporte GO/NO-GO**: tabla con las 6 secciones y su estado. Si todo GO,
   sugerir el tag de release y recordar que el commit final debe pasar los
   hooks (sin `--no-verify`).

## Notas

- Este skill NO ejecuta stages DVC ni toca artefactos congelados.
- Si `latexmk` no está en PATH: TinyTeX vive en
  `%APPDATA%\TinyTeX\bin\windows\`.
