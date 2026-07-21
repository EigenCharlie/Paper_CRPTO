# Contrato de superficies del companion CRPTO

`book/_quarto.yml` es la autoridad de navegación. Dentro de
`book/chapters/`, las únicas páginas activas son:

- `06-blueprint-manuscrito.qmd`: blueprint del manuscrito IJDS activo.
- `06b-guia-editorial-claims.qmd`: guía de claims y fronteras editoriales.

Fuera de este directorio, `book/index.qmd` y `book/references.qmd` completan el
companion activo. El body y el supplement autoritativos permanecen en
`paper/CRPTO_ijds.qmd` y `paper/supplement_ijds.qmd`.

## Fuentes históricas no autoritativas

Todas las demás QMD de este directorio están retiradas de la navegación y de la
evidencia activa. Se conservan únicamente como procedencia: pueden contradecir
el estimando, los datos, los resultados o los límites de claim vigentes y no
deben citarse como evidencia del manuscrito activo. Cada una contiene el
marcador uniforme
`<!-- crpto-companion-status: retired-historical-source -->`.

- `00-crpto-en-una-pagina.qmd`
- `00b-prologo-tesis.qmd`
- `01-introduccion.qmd`
- `02-marco-teorico.qmd`
- `03-metodologia.qmd`
- `04-resultados.qmd`
- `05-discusion.qmd`
- `07-apendice-robustez.qmd`
- `08-ablacion-mondrian.qmd`
- `09-spo-regret.qmd`
- `10-fair-lending.qmd`
- `11-mrm.qmd`
- `12-funded-set.qmd`
- `13-trazabilidad.qmd`
- `14-release.qmd`
- `15-fundamentos-riesgo-ml.qmd`
- `16-fundamentos-conformal-optimizacion.qmd`
- `17-pipeline-datos-features.qmd`
- `18-pd-calibracion-champion.qmd`
- `19-conformal-dossier.qmd`
- `20-portafolio-policy.qmd`
- `21-gobernanza-explicabilidad-dataset.qmd`
- `22-literatura-trazabilidad-entorno.qmd`
- `23-apendices-regulatorios-y-future-work.qmd`
- `24-bibliografia-crpto-actualizada.qmd`
- `25-reviewer-map.qmd`
- `26-sintesis-tesis.qmd`
- `27-conclusiones-tesis.qmd`
- `28-resultados-auxiliares.qmd`
- `29-ecl-incertidumbre.qmd`
- `30-replicacion-multidataset.qmd`
- `glosario.qmd`

Retirar una página de la navegación no borra su procedencia. Reactivarla exige
primero reconciliarla con el registro de claims activo y añadirla explícitamente
a `book/_quarto.yml`; el contenido histórico, por sí solo, no supera ese gate.
