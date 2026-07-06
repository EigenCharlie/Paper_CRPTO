---
name: crpto-claim-sync
description: Gate de sincronía de claims del paper - corre los tests de sync y coteja los números canónicos pool93 en qmd/tex contra el registro activo. Obligatorio tras cualquier edición de paper o supplement.
---

# /crpto-claim-sync

Verifica que todos los números paper-facing siguen sincronizados con los
artefactos de gobernanza pool93. Fuente de verdad editorial:
`docs/research/active_claims_2026-07-04.md` (o el registro que lo supersede).

## Pasos

1. **Tests de sincronía** (los tres deben pasar):
   ```powershell
   uv run pytest tests/test_pool93_body_claim_sync.py tests/test_crpto_final_sync.py tests/test_supplement_table_sync.py -q
   ```

2. **Cotejo de números canónicos** en las tres superficies editables
   (`paper/CRPTO_ijds.qmd`, `paper/supplement_ijds.qmd`,
   `paper/submission/CRPTO_ijds_submission.tex`). Buscar cada valor con Grep
   — ojo con el formato LaTeX `184{,}832.48` además de `184,832.48`:

   | Claim | Valor |
   | --- | --- |
   | Retorno body point | `$184,832.48` |
   | V(alpha=0.01) | `0.035350` |
   | Gamma_CP(alpha=0.01) | `0.162616` |
   | Markov cap | `0.345084` |
   | B_u endpoint | `0.245084` |
   | Alpha grid | `8/8`, violación exacta `0.0` |
   | Return floor | `$170,464.54` (solo como floor, nunca como headline) |
   | Frontera consolidada | `50,010` dedup / `27,508` elegibles |
   | Búsqueda terminal | `37,068` políticas / `296,544` checks |
   | Panel OOT | `276,869` préstamos |
   | Endpoint conservador | `$170,467.27`, cap `0.273036` |
   | Endpoint económico | `$223,458.14` |

3. **Divergencia qmd vs tex**: si un claim aparece en el `.qmd` con un valor y
   en el `.tex` con otro (o falta en uno), reportarlo — el `.qmd` es la fuente
   y el `.tex` debe portarse a mano.

4. **Reporte**: matriz claim x superficie con OK/FALTA/DIVERGE. Si todo OK,
   una sola línea verde. Si algo diverge, bloque con ubicaciones exactas
   (archivo:línea) y valor esperado; NO auto-corregir números sin confirmar
   con el usuario cuál es la fuente correcta.

## Notas

- Los valores canónicos de arriba son los del claim pool93 activo
  (2026-07-04). Si el registro activo cambió, actualizar esta tabla junto con
  el registro y `CLAUDE.md` en el mismo commit.
- Este gate NO valida hashes de artefactos (eso es `/crpto-validate-champion`);
  valida que la prosa no divergió de la gobernanza.
