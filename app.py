import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="VALORACIÓN CANTERA — Racing Club Ferrol",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Quita el padding por defecto de Streamlit para que el dashboard
# ocupe todo el ancho, sin marco extra alrededor.
st.markdown(
    """
    <style>
        .block-container {padding: 0 !important; max-width: 100% !important;}
        header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

BASE = Path(__file__).parent


def sync_enabled():
    try:
        return "gcp_service_account" in st.secrets and (BASE / "sync_config.json").exists()
    except Exception:  # sin secrets.toml
        return False

SYNC_TTL = 600  # segundos: cada cuánto se vuelve a leer Drive (10 min)


@st.cache_data(ttl=SYNC_TTL, show_spinner="Sincronizando con Drive…")
def build_dashboard():
    """Devuelve (html, cambios, error, avisos). Si Drive no está configurado o falla, sirve el dashboard.html del repo."""
    html = (BASE / "dashboard.html").read_text(encoding="utf-8")
    cfg_path = BASE / "sync_config.json"
    try:
        if not sync_enabled():
            return html, [], None, []  # sin sincronización configurada
        import sync_cantera as S

        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        sa = dict(st.secrets["gcp_service_account"])
        regs = [S.drive_download_xlsx(i, sa) for i in cfg["registro_ids"]]
        roster = S.drive_download_xlsx(cfg["roster_id"], sa) if cfg.get("roster_id") else None
        pls, avisos = [], []
        for x in cfg.get("pliegues", []):  # un archivo de pliegues sin compartir no debe bloquear el resto
            try:
                pls.append((S.drive_download_xlsx(x["id"], sa), x.get("categoria")))
            except Exception as e:
                avisos.append(f"Pliegues {x.get('categoria') or x['id']}: {type(e).__name__}: {e}")
        new_html, changes = S.run(html, regs, roster, stamp=True, pliegues=pls)
        return new_html, changes, None, avisos
    except Exception as e:  # nunca dejar la app sin datos por un fallo de Drive
        return html, [], f"{type(e).__name__}: {e}", []


html_content, changes, error, avisos = build_dashboard()

with st.sidebar:
    st.markdown("**Datos**")
    if error:
        st.warning("No se pudo sincronizar con Drive; se muestra la última versión guardada.\n\n" + error)
    elif sync_enabled():
        st.success(f"Sincronizado con Drive (se refresca cada {SYNC_TTL // 60} min). "
                   f"{len(changes)} novedad(es) respecto a la versión guardada.")
    else:
        st.info("Sincronización con Drive sin activar (ver README).")
    for a in avisos:
        st.warning("Archivo de pliegues no leído (¿compartido con la cuenta de servicio?). " + a)
    if st.button("🔄 Sincronizar ahora"):
        build_dashboard.clear()
        st.rerun()

# height fijo con scroll interno: el dashboard cambia de alto según la pestaña
# y al abrir una ficha. (st.iframe en Streamlit recientes; components.html como respaldo.)
if hasattr(st, "iframe"):
    st.iframe(html_content, height=2600)
else:
    components.html(html_content, height=2600, scrolling=True)
