# `scripts/archive/`

Scripts one-shot retirados del flujo activo (2026-06). No los invoca ningún
stage DVC, target de `justfile`, orquestador, test, capítulo del libro ni
documento; se conservan como evidencia histórica del proceso de búsqueda y
de auditorías ya congeladas en `models/*.json` y `reports/crpto/tables/`.

Política:

- Un script vive aquí solo si tiene **cero consumidores ejecutables** en el repo
  (verificado contra `dvc.yaml`, `justfile`, `run_crpto_pipeline.py`,
  `tests/`, `book/`, `docs/`, `notebooks/`, `.github/` y cross-imports).
- Los scripts cuyos outputs siguen siendo deps de DVC o cuyo rol en
  `configs/pipeline_registry/script_role_registry.yaml` es `core`/`paper`
  permanecen en `scripts/` aunque nadie los invoque hoy.
- No se garantiza que estos scripts corran con el stack de dependencias
  actual; reproducen estados históricos del pipeline.

| Script | Rol histórico |
| --- | --- |
| `build_concentration_bound_table.py` | Tabla exploratoria de bounds de concentración (no promovida al paper). |
| `run_crpto_notebook_suite.py` | Runner batch de la suite de notebooks exploratorios. |
| `search/compare_conformal_portfolio_finalists.py` | Comparación puntual de finalistas conformal durante la búsqueda. |
| `search/monitor_regret_auditability.py` | Monitor de progreso del sandbox de regret-auditability (cerrado 2026-05-28). |
| `search/resume_conformal_reopen_closure.py` | Reanudación del cierre de la búsqueda conformal reopen (run 2026-04-03/05). |
| `search/sweep_alpha_gamma_bound_finalists.py` | Sweep alpha-gamma sobre finalistas previo al exact eval. |
| `experiments/*.sh` | Launchers y monitores WSL/tmux de búsquedas June 2026 ya cerradas; se conservan sólo como provenance. |
| `monitor_regret_auditability.cmd` | Wrapper local roto del monitor que ya había sido archivado. |
