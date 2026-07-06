---
name: crpto-mrm-card
description: Actualiza o regenera la model card (skops) del champion en reports/mrm/. Lee del champion congelado.
---

# /crpto-mrm-card

Genera la model card del champion CRPTO para gobernanza MRM (Model Risk Management). Sigue lineamientos SR 11-7.

## Pasos

1. **Cargar champion**:
   ```python
   from catboost import CatBoostClassifier
   from pathlib import Path
   import json

   model = CatBoostClassifier()
   model.load_model("models/pd_canonical.cbm")
   promo = json.loads(Path("models/final_project_promotion.json").read_text())
   ```

2. **Generar model card via `skops`**:
   ```python
   from skops import card
   model_card = card.Card(model, metadata=card.metadata_from_config(Path("configs/crpto_pd_model.yaml")))
   model_card.add(model_description="PD champion CatBoost — Lending Club 2007-2020Q3")
   model_card.add_metrics(**promo["metrics"])
   ```

3. **Secciones requeridas (SR 11-7)**:
   - Model description (purpose, type, version)
   - Intended use (in-scope, out-of-scope)
   - Training data (source, time window, feature list, target)
   - Performance metrics (AUC, ECE, Brier, KS por cohorte)
   - Conformal coverage (90%/95% global + Mondrian por grade)
   - Fairness (DPD, EO, DIR por grupo)
   - Limitations and recommendations
   - Trazabilidad (run tag, DVC commit, artefactos)

4. **Guardar**:
   ```python
   output = Path("reports/mrm/model_card_crpto_champion.md")
   model_card.save(output)
   ```

5. **Validar contra EXTRACTION_MANIFEST**: asegurarse de que los hashes citados en la card coinciden con los del manifiesto.

## Argumentos

- Sin argumentos: regenera la card del champion.
- `--challenger <model_path>`: genera card de un modelo challenger para comparación.

## Notas

- La card sustituye `reports/mrm/model_card_crpto_champion.md` existente si lo hay.
- NO modifica el modelo, solo lee.
- Pre-check antes de empezar: `uv run python -c "import skops"`. Si falla, `uv add skops`.
