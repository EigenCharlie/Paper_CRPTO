---
name: crpto-validate-champion
description: Verifica que los artefactos del champion no han cambiado vs EXTRACTION_MANIFEST.json (hashes SHA256).
---

# /crpto-validate-champion

Verifica que el champion congelado sigue intacto. Sin efectos secundarios — pure read-only.

Vía rápida: `just validate-champion` corre `tests/test_manifest_regression.py`,
que ya barre todos los `critical_hashes` del manifiesto. Los pasos siguientes
son la versión manual/explicada.

## Pasos

1. **Cargar manifiesto**:
   ```python
   import json, hashlib
   from pathlib import Path
   manifest = json.loads(Path("EXTRACTION_MANIFEST.json").read_text())
   ```

2. **Listar artefactos críticos** del manifiesto (sección `critical_hashes`).
   Archivos clave:
   - `models/pd_canonical.cbm`
   - `models/pd_canonical_calibrator.pkl`
   - `models/final_project_promotion.json`
   - `models/conformal_policy_status.json`
   - `data/processed/conformal_intervals_mondrian.parquet`
   - `data/processed/portfolio_bound_aware/rank1_alpha01_bound_aware_276k_full_2026-04-05-1734/portfolio_bound_aware_bound_eval.parquet`
   - `reports/crpto/tables/crpto_tableA35..A39_pool93_*.csv/.tex` (evidencia pool93)
   - `models/experiments/champion_reopen/...__pool93__ijds-claim-bound-terminal/portfolio/pool93_ijds_claim_governance.json`
   - `models/experiments/champion_reopen/...__pool93__ijds-claim-consolidated-definitive/portfolio/pool93_ijds_consolidated_governance.json`

3. **Computar hashes SHA256** de cada archivo y comparar contra el manifiesto:
   ```python
   def sha256(p: Path) -> str:
       h = hashlib.sha256()
       with p.open("rb") as f:
           for chunk in iter(lambda: f.read(65536), b""):
               h.update(chunk)
       return h.hexdigest()
   ```

4. **Reportar**:
   - ✅ Artefactos con hash coincidente.
   - ❌ Artefactos con drift (path + esperado + actual).
   - ⚠️ Artefactos faltantes (en manifiesto pero no en disco).

5. **Verificar métricas paper (esquema dual-tag)**:
   - Cadena upstream congelada: `models/final_project_promotion.json` debe
     tener run tag `ijds-rebaseline-2026-06-07` y retorno `$170,464.54`.
   - Body claim pool93: `pool93_ijds_claim_governance.json` debe tener run tag
     `champion-reopen-2026-06-19__pool93__ijds-claim-bound-terminal` y
     `declared_return_floor = 170464.54`; el body point en
     `pool93_ijds_consolidated_governance.json` (`selected_candidates.paper_body`)
     debe reportar retorno `$184,832.48`, `V=0.035350`, `Γ_CP=0.162616`,
     Markov cap `0.345084`, alpha grid `8/8`.
   - Sincronía completa con el paper: `uv run pytest tests/test_pool93_body_claim_sync.py -q`.

## Salida

- Si todo OK: una línea verde "champion intacto, N artefactos verificados".
- Si drift: bloque con cada divergencia, sin sugerir auto-fix.
