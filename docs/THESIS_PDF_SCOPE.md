# Alcance Del PDF De Tesis APA

Fecha: 2026-06-08.

Este documento fija la decision operativa sobre el PDF largo de tesis. El libro
Quarto HTML es el companion vivo del proyecto; `paper/CRPTO_ijds.pdf` y
`paper/supplement_ijds.pdf` son borradores locales de verificacion para IJDS. El
PDF completo `CRPTO.pdf` del libro no se mantiene como artefacto rutinario.

## Decision

No vamos a sostener un PDF automatico de todo el libro Quarto. El libro completo
tiene demasiada superficie para un export unico: codigo largo, tablas anchas,
figuras pensadas para HTML, appendices granulares y paginas que funcionan bien
como dossier navegable pero no como documento APA paginado. Mantener ese PDF
agrega ruido editorial y no mejora el paper IJDS ni la tesis de maestria en su
estado actual.

Las superficies activas son:

| Superficie | Estado | Regla |
|---|---|---|
| Libro Quarto HTML | Mantener | Companion primario, navegable y amplio. |
| `CRPTO_ijds.pdf` | Mantener | Borrador HTML-print para revisar el paper; el PDF final usa plantilla IJDS. |
| `supplement_ijds.pdf` | Mantener | Borrador HTML-print para revisar el supplement. |
| `CRPTO.pdf` libro completo | No mantener | `just book-pdf` es no-op intencional. |
| PDF tesis APA | Diferir | Se construye despues como documento curado con secciones seleccionadas. |

## Cuando construir el PDF de tesis

El PDF APA de tesis se activa solo cuando exista una decision academica sobre:

1. Capitulos que entran al documento de maestria.
2. Norma APA y reglas institucionales vigentes.
3. Longitud objetivo y material que debe ir a apendices.
4. Figuras y tablas que realmente soportan la defensa.
5. Tratamiento de codigo: oculto, resumido o movido a apendice/repositorio.

Mientras falten esas decisiones, el trabajo correcto es fortalecer el libro HTML,
el paper IJDS y el supplement.

## Arquitectura recomendada

Cuando se active, el PDF de tesis debe ser un proyecto curado, no el libro
entero impreso:

| Componente | Recomendacion |
|---|---|
| Fuente | Nuevo perfil o carpeta `thesis/` que importe secciones seleccionadas del libro. |
| Ejecucion | `execute: false` / `freeze` contra artefactos ya validados; nunca reabre champion. |
| Estilo | APA 7, portada institucional, resumen, palabras clave, tabla de contenido, lista de figuras/tablas si aplica. |
| Codigo | Oculto en el cuerpo; fragmentos solo si son metodologicamente necesarios. |
| Tablas | Versiones compactas en cuerpo; tablas anchas a apendice landscape, CSV o HTML companion. |
| Figuras | PNG/PDF paper-grade con dimensiones fijas; ninguna figura debe ocupar pagina completa y quedar cortada. |
| Referencias | `book/references.bib` + `book/apa.csl`, auditadas antes del cierre. |
| Apendices | Solo material que un jurado pueda necesitar; no volcar A0--A34 completo sin curadoria. |

## Checklist de activacion

Antes de crear el PDF APA:

```powershell
just lint
just smoke
just validate-champion
just paper-submission-pdf
just book
```

Luego, para el documento de tesis:

1. Definir outline con maximo 6--8 capitulos principales.
2. Crear una matriz seccion -> claim -> evidencia -> figura/tabla.
3. Decidir que tablas se resumen y cuales quedan fuera del PDF.
4. Renderizar un PDF piloto de 20--30 paginas.
5. Revisar visualmente pagina por pagina: tablas, figuras, captions,
   referencias cruzadas, saltos de pagina y overflow.
6. Solo despues escalar al documento completo.

## No objetivos

- No convertir el libro completo en PDF por obligacion tecnica.
- No usar el PDF de tesis para reabrir la busqueda del champion.
- No duplicar el paper IJDS dentro de la tesis sin adaptarlo a la narrativa de
  maestria.
- No mantener `CRPTO.pdf` si su unica utilidad es detectar problemas de layout
  que ya sabemos que nacen de imprimir un dossier HTML de 400+ paginas.

La tesis debe ser mas selectiva que el libro y mas pedagogica que el paper. El
PDF APA se construira cuando esa seleccion este clara.
