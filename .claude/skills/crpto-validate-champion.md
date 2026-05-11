---
description: Verifica que los artefactos del champion no han cambiado vs EXTRACTION_MANIFEST.json (hashes SHA256).
---

# /crpto-validate-champion

Verifica que el champion congelado sigue intacto. Sin efectos secundarios — pure read-only.

## Pasos

1. **Cargar manifiesto**:
   ```python
   import json, hashlib
   from pathlib import Path
   manifest = json.loads(Path("EXTRACTION_MANIFEST.json").read_text())
   ```

2. **Listar artefactos críticos** del manifiesto (sección `critical_artifacts` o similar).
   Archivos típicos:
   - `models/pd_canonical.cbm`
   - `models/pd_canonical_calibrator.pkl`
   - `models/final_project_promotion.json`
   - `models/conformal_policy_status.json`
   - `data/processed/conformal_intervals_mondrian.parquet`
   - `data/processed/portfolio_bound_aware/rank1_alpha01_bound_aware_276k_full_2026-04-05-1734/portfolio_bound_aware_bound_eval.parquet`

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

5. **Verificar métricas paper**:
   - Leer `models/final_project_promotion.json`.
   - Confirmar que coincide con el run tag `paper-thesis-final-economic-2026-04-06` y retorno `$170,464.54`.

## Salida

- Si todo OK: una línea verde "champion intacto, N artefactos verificados".
- Si drift: bloque con cada divergencia, sin sugerir auto-fix.
