---
description: Pipeline completo de salida journal-ready - tablas, figuras, libro Quarto, journal package.
---

# /crpto-paper-export

Genera todos los artefactos publicables del paper en orden correcto. NO toca el champion congelado.

> ⚠️ **Alcance pool93**: las tablas A35–A39 y los JSONs de gobernanza pool93
> son outputs congelados de experimentos FUERA del DAG de DVC —
> `export_crpto_tables.py` NO los regenera (lee el promotion JSON del
> rebaseline congelado y solo regenera las tablas de esa cadena). Nunca
> sobreescribir A35–A39 con este pipeline. Tras cualquier export, correr
> `just validate-champion` para probar que los artefactos protegidos siguen
> bit-idénticos.

## Pasos

1. **Validar champion intacto**:
   ```powershell
   /crpto-validate-champion
   ```
   Si falla, abortar y reportar.

2. **Tablas** (subset regenerable del DAG; hoy hay 43 CSVs + 43 TEX en `reports/crpto/tables/`, de los cuales A35–A39 son congelados pool93):
   ```powershell
   uv run python scripts/export_crpto_tables.py
   ```

3. **Figuras** (hoy hay 21 PNGs + 21 PDFs en `reports/crpto/figures/`):
   ```powershell
   uv run python scripts/generate_crpto_figures.py --paper crpto
   ```

4. **Evidencia y journal package**:
   ```powershell
   uv run python scripts/analyze_crpto_evidence.py
   uv run python scripts/build_crpto_journal_package.py
   ```

5. **Render del libro**:
   ```powershell
   uv run -- quarto render book --to html
   ```

6. **Estatus final**: leer `models/crpto_journal_package_status.json` y reportar.

## Argumentos

- Sin argumentos: pipeline completo.
- `--quick`: solo tablas y figuras (sin journal package ni render).
- `--pdf`: añade `quarto render book --to pdf` al final.

## Resumen al usuario

- Tablas generadas: N CSVs (lista los nuevos o cambiados).
- Figuras generadas: N PNGs.
- Libro renderizado: ✅/❌.
- Journal package status: estado del JSON final.
- `just validate-champion` post-export: ✅/❌ (obligatorio; prueba que A35–A39 y demás artefactos protegidos no cambiaron).
