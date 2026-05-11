---
description: Smoke tests del proyecto - pytest crítico + dbt parse + dbt test. Rápido (~30s).
---

# /crpto-smoke

Verificación rápida de que el proyecto está sano. Ideal antes de commit o al inicio de sesión.

## Pasos

1. **Lint**:
   ```powershell
   uv run ruff check .
   uv run ruff format --check .
   ```

2. **Tests críticos**:
   ```powershell
   uv run pytest tests/test_crpto_final_sync.py tests/test_quarto_book_guardrails.py -q
   ```

3. **DBT sano**:
   ```powershell
   uv run dbt parse --project-dir dbt_project --profiles-dir dbt_project
   uv run dbt test --project-dir dbt_project --profiles-dir dbt_project
   ```

4. **DVC sin drift**:
   ```powershell
   uv run dvc status
   ```
   Si reporta `changed`, listar los stages afectados pero NO ejecutar `dvc repro`.

## Resumen al usuario

- Lint: ✅/❌ (errores si los hay).
- Tests críticos: N pass, M fail.
- DBT: parse + tests OK / fallos.
- DVC drift: stages con cambios pendientes (informativo).

Si todo verde, decirlo en una sola línea. Si algo falla, mostrar el error específico (no el output completo).
