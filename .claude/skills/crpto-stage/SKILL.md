---
name: crpto-stage
description: Ejecuta un stage DVC aislado con dry-run primero. Bloquea stages que tocan el champion congelado.
---

# /crpto-stage

Ejecuta un stage DVC específico con seguridad.

## Argumentos

- Nombre del stage (ej. `crpto.paper.export_tables`, `crpto.paper.figures`).

## Pasos

1. **Validar stage permitido**. Stages **bloqueados** sin permiso explícito del usuario:
   - `crpto.pd.champion`
   - `crpto.conformal.intervals`
   - `crpto.conformal.validation`
   - `crpto.portfolio.optimization`
   - `crpto.portfolio.bound_exact_eval`
   - `crpto.data.dataset` (lento, regenera todo downstream)
   - `crpto.data.features` (regenera train_fe/test_fe/calibration_fe)

   Si el usuario pide alguno de estos, pedir confirmación explícita y avisar de impacto en el champion.

2. **Dry-run**:
   ```powershell
   uv run dvc status <stage>
   uv run dvc repro --dry <stage>
   ```
   Reporta deps que cambiaron y outputs que se regenerarán.

3. **Ejecutar** (tras confirmación):
   ```powershell
   uv run dvc repro <stage>
   ```

4. **Validación post-run**:
   - `dvc status <stage>` debe quedar sin cambios.
   - Si el stage genera artefactos listados en `EXTRACTION_MANIFEST.json`, ejecutar `/crpto-validate-champion` para confirmar que los hashes coinciden.

5. **Resumen**: tiempo, outputs generados, líneas de log relevantes.

## Notas

- Trabaja siempre desde el root del repo.
- Costo: `crpto.data.dataset` procesa 1.7 GB y los stages PD/search re-puntúan ~514k filas — de minutos a horas. Reportar la estimación antes de ejecutar.
- Si el stage falla, no intentar arreglar automáticamente — reportar al usuario.
