# VALORACIÓN CANTERA — Racing Club Ferrol

Dashboard de la cantera (antropometría, pliegues, VALD, PHV, objetivos y baremos de Infantil).

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `dashboard.html` | El dashboard (HTML autocontenido con los datos embebidos). Es la "foto" base. |
| `app.py` | App de Streamlit. Muestra `dashboard.html` y, si la sincronización está activada, le aplica antes las mediciones nuevas del Excel de Drive. |
| `sync_cantera.py` | Lee los Excel de Drive y calcula las novedades (alturas, mediciones completas, **pliegues**, crecimiento, alertas PHV, percentiles, jugadores nuevos, nombres del roster). |
| `sync_config.json` | IDs de los archivos de Drive que se leen. |
| `requirements.txt` | Dependencias para Streamlit Community Cloud. |

## Qué se actualiza solo (con la sincronización activada)

Cada vez que alguien abre la app (como mucho cada 10 min) se lee Drive y se aplican las filas **nuevas** de
*Registro Valoraciones 1.1* (todas las hojas: CAD_A, CAD_B, INF_A, INF_B, JUV_B, Alevín, Senior Fem, INF_FEM) y de
*JUV_A_Registro Valoraciones 1.1*:

- **Solo altura** (como la medición de Cadete A del 13/10): actualiza altura, velocidad de crecimiento, alertas PHV,
  percentiles y curva de la categoría, y el histórico que usa el filtro de periodos de la pestaña PHV.
- **Medición completa** (perímetros, dorsiflexión, rotaciones): además recalcula asimetrías y avisos de riesgo.
- **Jugador que no estaba**: se crea con el nombre y equipo del roster (`ID_JUGADOR_RCF`).
- **Nombres y equipo** del roster: se refrescan.
- **Pliegues cutáneos** (*Infantil Pliegues* y *JUV_A Pliegues*): cada fila nueva actualiza Σ8, % graso y la pestaña
  Pliegues. Si el Excel trae **ID** (RCF_xxx) se usa tal cual; si solo trae **nombre** (como Infantil), el nombre se
  asocia solo al ID del roster (nombre exacto → sin tildes/espacios → apellidos de menos → parecido muy alto). Los
  vinculados de forma aproximada se marcan con ❓ y se listan en las notas de la pestaña. Si el archivo trae
  **Altura**, también actualiza la altura/crecimiento/PHV, y si el jugador no existe se crea con el nombre y equipo del roster.
  La fecha puede estar en una columna «Fecha», en la cabecera (p. ej. `28-09-2026 Nombre`) o en una fila superior.
- Avisos de calidad en la pestaña de datos: descensos de altura, saltos de más de 3 cm en menos de 100 días, IDs sin
  coincidencia, pliegues que no se pudieron vincular, sumatorios que no cuadran.

Reglas: solo se aplican filas con fecha **posterior** a la última que el dashboard ya tiene de ese jugador; en las
hojas la fecha puede ir solo en la primera fila (se arrastra hacia abajo); en Alevín, si no hay ID, se vincula por nombre.

**Nombres repetidos.** Si el roster tiene el mismo nombre bajo dos IDs (p. ej. RCF_039 y RCF_193, RCF_084 y RCF_194,
o varios Alevín) se consideran **personas distintas**: no se renombran ni se vinculan por nombre (solo por ID, o si la
categoría del archivo desempata). Aparece un aviso en la pestaña de datos hasta que se diferencien en el roster. Una
fila de pliegues con ese nombre y sin ID queda sin integrar (con aviso) hasta que le pongas el ID.

**Lo que NO es automático**: los tests **VALD** (siguen siendo carga manual: pídeme "actualiza los datos").

## Activar la sincronización (una sola vez, ~10 min)

1. **Cuenta de servicio de Google (solo lectura).** En <https://console.cloud.google.com>: crea un proyecto →
   *APIs y servicios* → habilita **Google Drive API** → *IAM y administración* → *Cuentas de servicio* → crear →
   en la cuenta: *Claves* → *Agregar clave* → JSON (se descarga un `.json`).
2. **Comparte los archivos de Drive** con el email de la cuenta de servicio (`...@...iam.gserviceaccount.com`) como
   **Lector**: *Registro Valoraciones 1.1 - RCF Cantera*, *JUV_A_Registro Valoraciones 1.1 - RCF Cantera*, *ID_JUGADOR_RCF*,
   *Infantil Pliegues* y *JUV_A Pliegues*. (Si añades otro Excel de pliegues, compártelo igual y agrégalo a `sync_config.json`.)
3. **Streamlit Community Cloud** → tu app → *Settings* → *Secrets* → pega (copiando los valores del `.json`):

   ```toml
   [gcp_service_account]
   type = "service_account"
   project_id = "..."
   private_key_id = "..."
   private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
   client_email = "...@...iam.gserviceaccount.com"
   client_id = "..."
   token_uri = "https://oauth2.googleapis.com/token"
   ```
4. **Sube al repositorio** estos archivos (raíz, junto a `app.py`): `dashboard.html`, `app.py`, `sync_cantera.py`,
   `sync_config.json`, `requirements.txt` → `git add . && git commit -m "Sincronización con Drive" && git push`.
5. Abre la app: en la barra lateral (flecha arriba a la izquierda) debe poner **"Sincronizado con Drive"**. Botón
   *Sincronizar ahora* para forzar. Si falla algo, la app muestra el último `dashboard.html` y el motivo del error.

> Nunca subas el `.json` de la cuenta de servicio al repositorio: va solo en *Secrets*.

## Ejecutar en local

```bash
pip install -r requirements.txt
streamlit run app.py
# o, para actualizar el HTML a partir de Excel descargados:
python sync_cantera.py --html dashboard.html --registro registro.xlsx --roster roster.xlsx \
    --pliegues infantil_pliegues.xlsx=Infantil --pliegues juv_a_pliegues.xlsx="Juvenil A"
```

## Actualización manual (si no activas la sincronización)

Sustituye `dashboard.html` en el repo por el nuevo, `git push`, y si no se ve: *Reboot app* y Ctrl+Shift+R.
