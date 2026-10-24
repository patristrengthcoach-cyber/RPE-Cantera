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
- Alevín

Cada categoría se selecciona desde un desplegable en la app. Los datos se leen en tiempo real desde el Google Sheet de respuestas del formulario ("CANTERA Wellness RPE RCF 26/27"), una pestaña por categoría.

> Nota: Juvenil A tiene su propio dashboard independiente (repo/app distinta), ya que su fuente de datos es un Google Sheet diferente.

## Archivos

- `app_categorias.py` — aplicación principal de Streamlit (`app.py` es una copia idéntica).
- `requirements.txt` — dependencias de Python (`streamlit`, `pandas`, `plotly`, `matplotlib`, `xhtml2pdf`, `openpyxl`).
- `logo.png` — escudo del club, usado en el informe PDF (opcional; si no está, se muestra un emblema "RCF").

## Funcionalidades

- Vistas Wellness, RPE Entrenamiento y RPE Partido, con filtros Mes > Semana > Día.
- Monitoreo de plantilla con ACWR y ficha individual (con borrado de selección).
- Minutos de entreno **por día y por categoría** (50 min por defecto; se cambian en el editor y el botón guarda solo el día elegido). Minutos de partido por jugador y partido.
- **Molestias activas**: solo las reportadas el último día con datos (o hoy); una molestia sale de la lista tras 2 entrenos sin reportarla; en rojo si lleva 3 o más días seguidos.
- **Sin control de carga**: aviso con los jugadores sin RPE el día de referencia.
- **Informe mensual en Excel** (desplegable "📅 Informe mensual", arriba): por mes y categoría, o todas las categorías en un ZIP. Hojas: Resumen por jugador, Entrenos, Partidos, Wellness, Molestias y Carga por día (con RPE, minutos, carga y molestias).
- Exportación a **PDF** del informe con la selección actual (KPIs, plantilla, ficha, gráficos, molestias y jugadores sin control).

## Cómo funciona la carga de datos

La app lee cada pestaña del Sheet por **nombre** (no por `gid` numérico), usando la URL de exportación CSV de Google:

```
https://docs.google.com/spreadsheets/d/<SHEET_ID>/gviz/tq?tqx=out:csv&sheet=<NOMBRE_PESTAÑA>
```

Esto requiere que el Sheet esté compartido como "Cualquier persona con el enlace puede ver". Los datos se cachean 10 minutos.

## Formatos de columnas soportados

El formulario tiene varias variantes según la categoría, definidas en el código:

- `COLS_ESTANDAR`: Cadete A, Cadete B, Juvenil B (16 columnas: wellness matutino + disponibilidad + RPE entreno/partido).
- `COLS_CON_PERIODO`: Senior Femenino (17 columnas, añade la pregunta del período entre DOMS y disponibilidad).
- `COLS_CON_PERIODO_SIN_DOMS`: Cadete Femenino (16 columnas, con período pero sin DOMS).
- `COLS_SOLO_RPE`: Infantil A, Infantil B, Infantil Femenino y Alevín (9 columnas, solo RPE post-sesión/partido).

El código reconoce las dos variantes de etiquetas de la pregunta "Responder después de": "WELLNESS" / "ENTRENAMIENTO" / "COMPETICION" y "Levantarme por la mañana" / "Sesión de ENTRENAMIENTO" / "COMPETICION / PARTIDO". Los códigos de jugador se normalizan (`RCF_007`) y las notas tipo "4 - Muy bien" se leen como número.

## Añadir una nueva categoría

Añade una entrada al diccionario `CATEGORIAS` al principio de `app_categorias.py` (y de `app.py`), con la etiqueta, el nombre exacto de la pestaña y el mapeo de columnas correspondiente. No hace falta tocar el resto del código.

## Despliegue

Desplegado en [Streamlit Community Cloud](https://streamlit.io/cloud), apuntando a este repositorio con el archivo principal correspondiente. Tras subir cambios a GitHub la app se reconstruye sola.

## Datos guardados localmente

Los minutos de entreno (por día) y de partido (por jugador y partido) se guardan por categoría en archivos JSON (`minutos_entreno_guardado_<categoria>.json` y `minutos_partido_por_jugador_<categoria>.json`), generados automáticamente por la app. En Streamlit Cloud estos archivos pueden perderse cuando la app se reinicia o se vuelve a desplegar.
