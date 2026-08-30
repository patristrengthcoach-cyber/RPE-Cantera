# RCF Cantera - Control de Carga y Wellness

Dashboard en Streamlit para el monitoreo de rendimiento, wellness y carga de entrenamiento/partido de las categorías de cantera del Racing Club de Ferrol.

## Categorías incluidas

- Cadete A
- Cadete B
- Juvenil B
- Infantil A
- Infantil B
- Senior Femenino
- Cadete Femenino
- Infantil Femenino

Cada categoría se selecciona desde un desplegable en la app. Los datos se leen en tiempo real desde el Google Sheet de respuestas del formulario ("CANTERA Wellness RPE RCF 26/27"), una pestaña por categoría.

> Nota: Juvenil A tiene su propio dashboard independiente (repo/app distinta), ya que su fuente de datos es un Google Sheet diferente.

## Archivos

- `app_categorias.py` — aplicación principal de Streamlit.
- `requirements.txt` — dependencias de Python.
- `logo.png` — escudo del club, mostrado en la cabecera (opcional; si no está presente, se muestra un emoji ⚽).

## Cómo funciona la carga de datos

La app lee cada pestaña del Sheet por **nombre** (no por `gid` numérico), usando la URL de exportación CSV de Google:

```
https://docs.google.com/spreadsheets/d/<SHEET_ID>/gviz/tq?tqx=out:csv&sheet=<NOMBRE_PESTAÑA>
```

Esto requiere que el Sheet esté compartido como "Cualquier persona con el enlace puede ver".

## Formatos de columnas soportados

El formulario tiene 3 variantes según la categoría, definidas en `app_categorias.py`:

- `COLS_ESTANDAR`: Cadete A, Cadete B, Juvenil B (16 columnas, incluye wellness matutino + disponibilidad + RPE entreno/partido).
- `COLS_CON_PERIODO`: Senior Femenino (17 columnas, añade la pregunta del período entre DOMS y disponibilidad).
- `COLS_CON_PERIODO_SIN_DOMS`: Cadete Femenino (16 columnas, como `COLS_CON_PERIODO` pero sin la pregunta de DOMS).
- `COLS_SOLO_RPE`: Infantil A, Infantil B, Infantil Femenino (9 columnas, sin preguntas de wellness matutino, solo RPE post-sesión/partido).

> Nota: el formulario de las categorías femeninas más recientes (Cadete Femenino, Infantil Femenino) usa etiquetas distintas en la pregunta "¿Cuándo respondes?": "Levantarme por la mañana" / "Sesión de ENTRENAMIENTO" / "COMPETICION / PARTIDO", en vez de los literales "WELLNESS" / "ENTRENAMIENTO" / "COMPETICION" de las categorías más antiguas. El código ya reconoce ambas variantes.

## Añadir una nueva categoría

Solo hay que añadir una entrada al diccionario `CATEGORIAS` al principio de `app_categorias.py`, indicando la etiqueta, la URL del Sheet (o pestaña) y el mapeo de columnas correspondiente. No hace falta tocar el resto del código.

## Despliegue

Desplegado en [Streamlit Community Cloud](https://streamlit.io/cloud), apuntando a este repositorio con `app_categorias.py` como archivo principal.

## Datos guardados localmente

Los minutos de entreno y de partido introducidos manualmente se guardan por categoría en archivos JSON (`minutos_entreno_guardado_<categoria>.json` y `minutos_partido_por_jugador_<categoria>.json`), generados automáticamente por la app.
