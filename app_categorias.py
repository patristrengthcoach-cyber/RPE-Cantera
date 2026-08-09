import io
import json
import math
import os
import urllib.parse
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage

# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================
st.set_page_config(
    page_title="RCF - Control de Carga",
    page_icon="⚽",
    layout="wide",
)

NOMBRES_MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]
DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# ============================================================
# MAPEOS DE COLUMNAS (0 = columna A), según la plantilla del formulario
# ============================================================
COLS_ESTANDAR = {
    "timestamp": 0, "id_nombre": 1, "tipo": 2,
    "fatiga": 3, "sueno": 4, "orina": 5, "estres": 6,
    "molestia_manana": 7, "doms": 8,
    "disponible": 9,
    "rpe_entreno": 10, "molestia_entreno": 11, "rendimiento_entreno": 12,
    "rpe_partido": 13, "molestia_partido": 14, "rendimiento_partido": 15,
}

# SENIOR_FEM tiene una columna extra ("¿Estás con el período hoy?") entre DOMS
# y disponibilidad, por lo que el resto de columnas se desplaza una posición.
COLS_CON_PERIODO = {
    "timestamp": 0, "id_nombre": 1, "tipo": 2,
    "fatiga": 3, "sueno": 4, "orina": 5, "estres": 6,
    "molestia_manana": 7, "doms": 8, "periodo": 9,
    "disponible": 10,
    "rpe_entreno": 11, "molestia_entreno": 12, "rendimiento_entreno": 13,
    "rpe_partido": 14, "molestia_partido": 15, "rendimiento_partido": 16,
}

# Infantil A / Infantil B no tienen preguntas de wellness matutino (sin fatiga,
# sueño, estrés, DOMS ni disponibilidad): solo registran RPE post-sesión/partido.
COLS_SOLO_RPE = {
    "timestamp": 0, "id_nombre": 1, "tipo": 2,
    "rpe_entreno": 3, "molestia_entreno": 4, "rendimiento_entreno": 5,
    "rpe_partido": 6, "molestia_partido": 7, "rendimiento_partido": 8,
}

# ID del Sheet maestro: "CANTERA Wellness RPE RCF 26/27 (respuestas)"
# (pestañas: Senior Femenino, Infantil B, Infantil A, Cadete B, Cadete A, Juvenil B)
MASTER_SHEET_ID = "16yX64C2mFz8UCBCtOvZ_gIJX8rqLPvNt0kkjpLIyikc"


def _csv_url_por_hoja(sheet_id: str, sheet_name: str) -> str:
    """Carga por NOMBRE de pestaña (no requiere gid numérico). Los nombres con
    espacios se codifican para la URL."""
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(sheet_name)}"


# ============================================================
# CATEGORÍAS DISPONIBLES
# Añade/edita entradas aquí para sumar nuevas categorías sin tocar el resto del código.
# ============================================================
CATEGORIAS = {
    "cadete_a": {
        "label": "Cadete A",
        "csv_url": _csv_url_por_hoja(MASTER_SHEET_ID, "Cadete A"),
        "cols": COLS_ESTANDAR,
    },
    "cadete_b": {
        "label": "Cadete B",
        "csv_url": _csv_url_por_hoja(MASTER_SHEET_ID, "Cadete B"),
        "cols": COLS_ESTANDAR,
    },
    "juvenil_b": {
        "label": "Juvenil B",
        "csv_url": _csv_url_por_hoja(MASTER_SHEET_ID, "Juvenil B"),
        "cols": COLS_ESTANDAR,
    },
    "infantil_a": {
        "label": "Infantil A",
        "csv_url": _csv_url_por_hoja(MASTER_SHEET_ID, "Infantil A"),
        "cols": COLS_SOLO_RPE,
    },
    "infantil_b": {
        "label": "Infantil B",
        "csv_url": _csv_url_por_hoja(MASTER_SHEET_ID, "Infantil B"),
        "cols": COLS_SOLO_RPE,
    },
    "senior_fem": {
        "label": "Senior Femenino",
        "csv_url": _csv_url_por_hoja(MASTER_SHEET_ID, "Senior Femenino"),
        "cols": COLS_CON_PERIODO,
    },
}

st.markdown(
    """
    <style>
    .stApp { background-color: #030712; }
    [data-testid="stMetricValue"] { font-weight: 800; }
    [data-testid="stMetricLabel"] { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; }
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * { color: #d1d5db !important; }
    small { color: #d1d5db !important; }
    [data-testid="stMarkdownContainer"] p { color: #e5e7eb; }
    /* Filtros: misma estética oscura que el resto de cuadros */
    .st-key-filtros_box {
        background: linear-gradient(180deg, #0f172a 0%, #0a0f1c 100%) !important;
        border: 1px solid #1e293b !important; border-radius: 10px; padding: 0.35rem 0.6rem !important;
    }
    .st-key-filtros_box label, .st-key-filtros_box [data-testid="stMarkdownContainer"] p,
    .st-key-filtros_box [data-testid="stCaptionContainer"], .st-key-filtros_box [data-testid="stCaptionContainer"] * {
        color: #e5e7eb !important; font-weight: 600; font-size: 0.75rem !important;
    }
    .st-key-filtros_box [data-baseweb="select"] { font-size: 0.75rem !important; min-height: 2.1rem !important; }
    /* Selector de categoría: misma estética que los filtros */
    .st-key-categoria_box {
        background: linear-gradient(180deg, #0f172a 0%, #0a0f1c 100%) !important;
        border: 1px solid #1e293b !important; border-radius: 10px; padding: 0.35rem 0.6rem !important;
    }
    .st-key-categoria_box label, .st-key-categoria_box [data-testid="stMarkdownContainer"] p {
        color: #e5e7eb !important; font-weight: 700; font-size: 0.75rem !important;
    }
    .st-key-categoria_box [data-baseweb="select"] { font-size: 0.85rem !important; min-height: 2.1rem !important; }
    /* KPIs: caja muy resaltada */
    .st-key-kpi_box {
        background: linear-gradient(180deg, #0f172a 0%, #0a0f1c 100%) !important;
        border: 2px solid #155e63 !important;
        border-radius: 16px;
        padding: 1.1rem 0.75rem !important;
        box-shadow: 0 0 0 1px rgba(45,212,191,0.12), 0 10px 28px rgba(0,0,0,0.4);
    }
    /* Buscador y botones de la plantilla: más pequeños */
    [class*="st-key-buscar_input"] input { font-size: 0.8rem !important; padding: 0.35rem 0.6rem !important; color: #f1f5f9 !important; }
    [class*="st-key-borrar_sel"] button { font-size: 0.72rem !important; padding: 0.3rem 0.4rem !important; }
    [class*="st-key-verficha_"] button {
        font-size: 0.62rem !important; padding: 0.15rem 0.3rem !important; min-height: 1.6rem !important;
        background-color: #0891b2 !important; border-color: #0891b2 !important; color: #ffffff !important;
    }
    [class*="st-key-verficha_"] button:hover { background-color: #0e7490 !important; border-color: #0e7490 !important; color: #ffffff !important; }
    /* Tarjetas de jugadores más compactas */
    .st-key-roster_scroll [data-testid="stVerticalBlockBorderWrapper"] { padding: 0.25rem 0.5rem !important; }
    [class*="_inactivo"] button {
        color: #111827 !important;
        background-color: #e2e8f0 !important;
        font-weight: 700 !important;
        border: 1px solid #cbd5e1 !important;
    }
    [class*="_inactivo"] button:hover {
        background-color: #cbd5e1 !important;
        color: #0f172a !important;
    }
    /* Paneles Monitoreo / Ficha Individual: cuadros bien diferenciados con sombra */
    .st-key-panel_monitoreo, .st-key-panel_ficha {
        background: linear-gradient(180deg, #0f172a 0%, #0a0f1c 100%) !important;
        border: 1px solid #1e293b !important;
        border-radius: 14px;
        box-shadow: 0 10px 24px rgba(0,0,0,0.4);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# CARGA DE DATOS
# ============================================================
def valor(row, idx):
    if idx >= len(row):
        return None
    v = row.iloc[idx]
    return None if pd.isna(v) else v


def a_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parsear_id_nombre(texto):
    if texto is None:
        return None, None
    texto = str(texto).strip()
    partes = texto.split(" ", 1)
    if len(partes) == 2:
        return partes[0].strip(), partes[1].strip()
    return texto, texto


def color_carga(ua):
    if ua <= 200:
        return "#16a34a"
    if ua <= 400:
        return "#4ade80"
    if ua <= 600:
        return "#facc15"
    if ua <= 800:
        return "#fb923c"
    if ua <= 1000:
        return "#ef4444"
    return "#991b1b"


def color_escala_1_5(v):
    """1 = poco fatigado / nada estresado / sin DOMS (bueno) -> verde
    5 = muy fatigado / muy estresado / mucho DOMS (malo) -> rojo"""
    if v is None:
        return "#6b7280"
    if v <= 2:
        return "#16a34a"
    if v <= 3.2:
        return "#facc15"
    return "#ef4444"


def badge_escala(valor_num):
    color = color_escala_1_5(valor_num)
    texto = f"{valor_num:g}" if valor_num is not None else "—"
    return f"<span style='color:{color}; font-weight:800; font-size:1.4rem'>{texto}</span>"


def color_rpe(v):
    """RPE en escala 0-10 (Borg CR10): 0-3 suave, 4-5 moderado, 6-7 duro, 8-10 muy duro."""
    if v is None:
        return "#9ca3af"
    if v <= 3:
        return "#16a34a"
    if v <= 5:
        return "#facc15"
    if v <= 7:
        return "#fb923c"
    return "#ef4444"


def render_kpi(label, valor, color="#f1f5f9"):
    st.markdown(
        f"<div style='text-align:center; font-size:0.7rem; text-transform:uppercase; letter-spacing:0.05em; "
        f"color:#9ca3af; font-weight:700;'>{label}</div>"
        f"<div style='text-align:center; font-size:1.8rem; font-weight:800; color:{color}; line-height:1.2;'>{valor}</div>",
        unsafe_allow_html=True,
    )


def render_section_title(texto):
    st.markdown(
        f"<div style='font-size:1.05rem; font-weight:800; color:#ffffff; "
        f"border-left:4px solid #10b981; padding-left:10px; margin:0.2rem 0 0.7rem 0;'>{texto}</div>",
        unsafe_allow_html=True,
    )


def _fig_a_imagen_bytes(fig, width=1000, height=450):
    """Exporta una figura de Plotly a PNG con fondo claro, apta para imprimir en PDF."""
    try:
        fig_export = go.Figure(fig)
        fig_export.update_layout(
            template="plotly_white",
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=dict(color="#0f172a"),
        )
        return fig_export.to_image(format="png", width=width, height=height, scale=2)
    except Exception:
        return None


def generar_pdf_informe(
    categoria_label,
    vista_label,
    filtros_texto,
    kpis,
    columnas_tabla,
    filas_tabla,
    jugador_info,
    fig_evolucion,
    fig_semana,
    subtitulo_semana,
):
    """Construye un informe PDF con el resumen de KPIs, la tabla de la plantilla
    filtrada (según categoría/vista/filtros actuales), la ficha del jugador
    seleccionado (si hay uno) y los gráficos de carga."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle("TituloRCF", parent=styles["Title"], fontSize=18, textColor=colors.HexColor("#0f172a"))
    estilo_subtitulo = ParagraphStyle("SubtituloRCF", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#475569"), spaceAfter=4)
    estilo_seccion = ParagraphStyle("SeccionRCF", parent=styles["Heading2"], fontSize=13, textColor=colors.HexColor("#0f172a"), spaceBefore=14, spaceAfter=6)
    estilo_normal = styles["Normal"]

    elementos = [
        Paragraph("Racing Club de Ferrol — Informe de Rendimiento", estilo_titulo),
        Paragraph(f"Categoría: <b>{categoria_label}</b> · Vista: <b>{vista_label}</b>", estilo_subtitulo),
        Paragraph(f"Filtros aplicados: {filtros_texto}", estilo_subtitulo),
        Paragraph(f"Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}", estilo_subtitulo),
        Spacer(1, 10),
    ]

    elementos.append(Paragraph("Resumen", estilo_seccion))
    tabla_kpi = Table([[k for k, _ in kpis], [v for _, v in kpis]], hAlign="LEFT")
    tabla_kpi.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    elementos.append(tabla_kpi)

    elementos.append(Paragraph("Plantilla — Selección actual", estilo_seccion))
    if len(filas_tabla) > 0:
        tabla = Table([columnas_tabla] + filas_tabla, hAlign="LEFT", repeatRows=1)
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#10b981")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        elementos.append(tabla)
    else:
        elementos.append(Paragraph("Sin registros para esta selección.", estilo_normal))

    if jugador_info:
        elementos.append(Paragraph(f"Ficha Individual — {jugador_info['nombre']}", estilo_seccion))
        elementos.append(Paragraph(
            f"Código: {jugador_info['id']} · ACWR: {jugador_info['acwr']} · "
            f"Disponibilidad: {jugador_info['disponibilidad']} · Molestias: {jugador_info['molestias']}",
            estilo_normal,
        ))
        if jugador_info.get("detalle"):
            elementos.append(Spacer(1, 4))
            elementos.append(Paragraph(jugador_info["detalle"], estilo_normal))

    if fig_evolucion is not None:
        img_bytes = _fig_a_imagen_bytes(fig_evolucion)
        if img_bytes:
            elementos.append(Paragraph("Evolución de la Carga (sRPE, últimos 7 días)", estilo_seccion))
            elementos.append(RLImage(io.BytesIO(img_bytes), width=17 * cm, height=17 * cm * 450 / 1000))

    if fig_semana is not None:
        img_bytes = _fig_a_imagen_bytes(fig_semana)
        if img_bytes:
            elementos.append(Paragraph(f"Carga por Día de la Semana — {subtitulo_semana}", estilo_seccion))
            elementos.append(RLImage(io.BytesIO(img_bytes), width=17 * cm, height=17 * cm * 450 / 1000))

    doc.build(elementos)
    buffer.seek(0)
    return buffer.getvalue()


def _minutos_entreno_file(categoria_key):
    return f"minutos_entreno_guardado_{categoria_key}.json"


def _minutos_partido_file(categoria_key):
    return f"minutos_partido_por_jugador_{categoria_key}.json"


def cargar_minutos_entreno_guardado(categoria_key):
    try:
        with open(_minutos_entreno_file(categoria_key), "r") as f:
            return int(json.load(f).get("entreno", 75))
    except Exception:
        return 75


def guardar_minutos_entreno_en_disco(categoria_key, entreno):
    try:
        with open(_minutos_entreno_file(categoria_key), "w") as f:
            json.dump({"entreno": entreno}, f)
        return True
    except Exception:
        return False


def cargar_minutos_partido_guardados(categoria_key):
    """Devuelve un diccionario {'idJugador|fecha': minutos}."""
    try:
        with open(_minutos_partido_file(categoria_key), "r") as f:
            return json.load(f)
    except Exception:
        return {}


def guardar_minutos_partido_en_disco(categoria_key, id_jugador, fecha, minutos):
    datos = cargar_minutos_partido_guardados(categoria_key)
    datos[f"{id_jugador}|{fecha}"] = minutos
    try:
        with open(_minutos_partido_file(categoria_key), "w") as f:
            json.dump(datos, f)
        return True
    except Exception:
        return False


SIN_MOLESTIA_TEXTOS = {"no", "nada", "ninguna", "ningun", "ningún", "sin molestias", ""}


def calcular_racha_molestias(historial_jugador: pd.DataFrame):
    """Recorre TODOS los registros (wellness/entreno/partido) de un jugador y calcula
    cuántos días seguidos lleva reportando alguna molestia (excluyendo 'no'/'nada').
    Devuelve (racha_en_dias, texto_de_la_molestia_actual)."""
    por_dia = {}
    for _, r in historial_jugador.iterrows():
        fecha = r["fecha"]
        mol = r.get("molestias")
        tiene = mol is not None and str(mol).strip().rstrip(".").lower() not in SIN_MOLESTIA_TEXTOS
        if fecha not in por_dia:
            por_dia[fecha] = {"tiene": False, "texto": "Sin molestias"}
        if tiene:
            por_dia[fecha]["tiene"] = True
            por_dia[fecha]["texto"] = str(mol).strip()
    dias_ordenados = sorted(por_dia.keys(), key=lambda d: pd.to_datetime(d, dayfirst=True))
    racha = 0
    texto_actual = "Sin molestias"
    for fecha in reversed(dias_ordenados):
        info = por_dia[fecha]
        if info["tiene"]:
            racha += 1
            if racha == 1:
                texto_actual = info["texto"]
        else:
            break
    return racha, texto_actual


def ordenar_semanas_desc(semanas):
    def fecha_de_semana(s):
        try:
            return pd.to_datetime(s.replace("Semana ", ""), dayfirst=True)
        except Exception:
            return pd.Timestamp.min
    return sorted(semanas, key=fecha_de_semana, reverse=True)


def procesar_registros(df_raw: pd.DataFrame, cols: dict):
    """Convierte las filas crudas del Form en registros clasificados por tipo,
    y mantiene un 'último estado conocido' (wellness/disponibilidad/molestias) por jugador.
    `cols` es el mapeo de columnas específico de la categoría (permite plantillas
    de formulario ligeramente distintas, p.ej. SENIOR_FEM con la pregunta del período)."""
    filas = []
    for _, row in df_raw.iterrows():
        ts_raw = valor(row, cols["timestamp"])
        if ts_raw is None:
            continue
        ts = pd.to_datetime(ts_raw, dayfirst=True, errors="coerce")
        if pd.isna(ts):
            continue
        id_j, nombre = parsear_id_nombre(valor(row, cols["id_nombre"]))
        if not id_j:
            continue
        tipo_raw = str(valor(row, cols["tipo"]) or "").strip().upper()
        if "WELLNESS" in tipo_raw:
            tipo = "WELLNESS"
        elif "ENTREN" in tipo_raw:
            tipo = "ENTRENO"
        elif "PARTIDO" in tipo_raw or "COMPETICION" in tipo_raw:
            tipo = "PARTIDO"
        else:
            tipo = "OTRO"
        inicio_semana = ts - pd.Timedelta(days=ts.weekday())
        fila = {
            "timestamp": ts,
            "fecha": ts.strftime("%d/%m/%Y"),
            "semana": f"Semana {inicio_semana.strftime('%d/%m/%Y')}",
            "mes": NOMBRES_MESES[ts.month - 1],
            "idJugador": id_j,
            "nombre": nombre,
            "tipo": tipo,
        }
        if tipo == "WELLNESS":
            fila["fatiga"] = a_float(valor(row, cols["fatiga"]))
            fila["sueno"] = a_float(valor(row, cols["sueno"]))
            fila["orina"] = a_float(valor(row, cols["orina"]))
            fila["estres"] = a_float(valor(row, cols["estres"]))
            fila["doms"] = a_float(valor(row, cols["doms"]))
            if "periodo" in cols:
                periodo_raw = valor(row, cols["periodo"])
                fila["periodo"] = str(periodo_raw).strip() if periodo_raw not in (None, "") else None
            escalas = [v for v in [fila["fatiga"], fila["sueno"], fila["estres"], fila["doms"]] if v is not None]
            fila["wellness_score"] = sum(escalas) / len(escalas) if escalas else None
            disp_raw = valor(row, cols["disponible"])
            fila["disponible"] = str(disp_raw).strip().upper() if disp_raw is not None else None
            mol = valor(row, cols["molestia_manana"])
            fila["molestias"] = str(mol).strip() if mol not in (None, "") else "Sin molestias"
            fila["rpe"] = None
        elif tipo == "ENTRENO":
            fila["rpe"] = a_float(valor(row, cols["rpe_entreno"]))
            mol = valor(row, cols["molestia_entreno"])
            fila["molestias"] = str(mol).strip() if mol not in (None, "") else "Sin molestias"
            fila["rendimiento"] = a_float(valor(row, cols["rendimiento_entreno"]))
        elif tipo == "PARTIDO":
            fila["rpe"] = a_float(valor(row, cols["rpe_partido"]))
            mol = valor(row, cols["molestia_partido"])
            fila["molestias"] = str(mol).strip() if mol not in (None, "") else "Sin molestias"
            fila["rendimiento"] = a_float(valor(row, cols["rendimiento_partido"]))
        else:
            continue  # fila sin tipo reconocible, se ignora
        filas.append(fila)
    df = pd.DataFrame(filas)
    if df.empty:
        return df, {}
    df = df.sort_values("timestamp")
    # "Último estado conocido" por jugador, recorriendo cronológicamente
    estados = {}
    for _, r in df.iterrows():
        idj = r["idJugador"]
        if idj not in estados:
            estados[idj] = {"wellness": None, "disponibilidad": "DISPONIBLE", "molestias": "Sin molestias"}
        if r["tipo"] == "WELLNESS":
            if r.get("wellness_score") is not None:
                estados[idj]["wellness"] = r["wellness_score"]
            disp_val = r.get("disponible")
            if disp_val:
                if disp_val.startswith("NO"):
                    estados[idj]["disponibilidad"] = "NO DISPONIBLE"
                elif disp_val.startswith("SI") or disp_val.startswith("SÍ"):
                    estados[idj]["disponibilidad"] = "DISPONIBLE"
        estados[idj]["molestias"] = r.get("molestias", estados[idj]["molestias"])
    return df, estados


@st.cache_data(ttl=600)
def cargar_y_procesar(categoria_key: str):
    config = CATEGORIAS[categoria_key]
    df_raw = pd.read_csv(config["csv_url"], header=0)
    return procesar_registros(df_raw, config["cols"])


# ============================================================
# ACWR — carga aguda 7d / carga crónica media hasta 4 semanas
# ============================================================
def calcular_acwr(historial_srpe: pd.DataFrame, timestamp_ref: pd.Timestamp):
    if historial_srpe.empty:
        return "N/A", "verde"
    primer_registro = historial_srpe["timestamp"].min()
    dias_en_bd = (timestamp_ref - primer_registro).days
    semanas_activas = max(1, math.ceil(dias_en_bd / 7))
    divisor_cronico = min(semanas_activas, 4)
    agudo = historial_srpe[
        (historial_srpe["timestamp"] >= timestamp_ref - pd.Timedelta(days=6))
        & (historial_srpe["timestamp"] <= timestamp_ref)
    ]["srpe"].sum()
    cronico = historial_srpe[
        (historial_srpe["timestamp"] >= timestamp_ref - pd.Timedelta(days=27))
        & (historial_srpe["timestamp"] <= timestamp_ref)
    ]["srpe"].sum()
    media_cronica = cronico / divisor_cronico if divisor_cronico else 0
    if media_cronica == 0:
        return (">2.00", "rojo") if agudo > 0 else ("N/A", "verde")
    acwr = agudo / media_cronica
    if acwr > 1.5:
        color = "rojo"
    elif acwr >= 1.3 or acwr < 0.8:
        color = "amarillo"
    else:
        color = "verde"
    return f"{acwr:.2f}", color


# ============================================================
# SELECTOR DE CATEGORÍA
# ============================================================
if "categoria_key" not in st.session_state:
    st.session_state["categoria_key"] = list(CATEGORIAS.keys())[0]

col_logo, col_titulo, col_cat = st.columns([1, 6, 3])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=70)
    else:
        st.markdown("<div style='font-size:2.5rem'>⚽</div>", unsafe_allow_html=True)
with col_titulo:
    st.markdown(
        "<div style='font-size:1.9rem; font-weight:900; color:#ffffff; letter-spacing:0.01em; line-height:1.15;'>RACING CLUB DE FERROL</div>",
        unsafe_allow_html=True,
    )
    cat_actual_label = CATEGORIAS[st.session_state["categoria_key"]]["label"]
    st.caption(f"DIRECCIÓN DE RENDIMIENTO Y SALUD • {cat_actual_label.upper()}")
with col_cat:
    with st.container(border=True, key="categoria_box"):
        st.selectbox(
            "Categoría",
            options=list(CATEGORIAS.keys()),
            format_func=lambda k: CATEGORIAS[k]["label"],
            key="categoria_key",
        )

# ============================================================
# EXPORTAR INFORME PDF
# El botón se ve aquí, arriba de todo, pero se rellena al final del script
# (una vez calculados la plantilla filtrada, KPIs y gráficos de esta selección).
# ============================================================
pdf_placeholder = st.container()

# Si el usuario cambia de categoría, reseteamos la selección de jugador
# (el índice de la fila seleccionada no tiene sentido en otro dataset).
if st.session_state.get("_categoria_previa") != st.session_state["categoria_key"]:
    st.session_state["_categoria_previa"] = st.session_state["categoria_key"]
    st.session_state["jugador_sel_idx"] = None

categoria_key = st.session_state["categoria_key"]
CATEGORIA = CATEGORIAS[categoria_key]["label"]

with st.spinner("Estableciendo conexión con el Google Sheet..."):
    try:
        df, estados = cargar_y_procesar(categoria_key)
    except Exception as e:
        st.error("❌ No se han podido cargar los datos. Revisa que el Sheet siga siendo público para lectura.")
        st.exception(e)
        st.stop()

if df.empty:
    st.warning("Conexión correcta, pero todavía no hay respuestas registradas en el formulario para esta categoría.")
    st.stop()

# ============================================================
# VISTA (botones resaltados) + MINUTOS DE ENTRENO (global, con guardado)
# ============================================================
if "vista_key" not in st.session_state:
    st.session_state["vista_key"] = "wellness"

minutos_guardados_entreno = cargar_minutos_entreno_guardado(categoria_key)

col_vista, col_min = st.columns([2, 1])
with col_vista:
    cv1, cv2, cv3 = st.columns(3)
    with cv1:
        activo_w = st.session_state["vista_key"] == "wellness"
        if st.button("🧠 Wellness", use_container_width=True, type="primary" if activo_w else "secondary",
                      key=f"vista_wellness_{'activo' if activo_w else 'inactivo'}"):
            st.session_state["vista_key"] = "wellness"
            st.rerun()
    with cv2:
        activo_e = st.session_state["vista_key"] == "rpe_entreno"
        if st.button("⚽ RPE Entrenamiento", use_container_width=True, type="primary" if activo_e else "secondary",
                      key=f"vista_entreno_{'activo' if activo_e else 'inactivo'}"):
            st.session_state["vista_key"] = "rpe_entreno"
            st.rerun()
    with cv3:
        activo_p = st.session_state["vista_key"] == "rpe_partido"
        if st.button("🔥 RPE Partido", use_container_width=True, type="primary" if activo_p else "secondary",
                      key=f"vista_partido_{'activo' if activo_p else 'inactivo'}"):
            st.session_state["vista_key"] = "rpe_partido"
            st.rerun()
with col_min:
    cmin1, cmin2 = st.columns([1, 0.4])
    with cmin1:
        minutos_entreno = st.number_input(
            "Min. Entreno (equipo)", min_value=1, value=minutos_guardados_entreno, step=5,
            key=f"min_entreno_input_{categoria_key}",
        )
    with cmin2:
        st.markdown("<div style='height:1.85rem'></div>", unsafe_allow_html=True)
        if st.button("💾", help="Guardar minutos de entreno para próximas visitas", key=f"guardar_min_entreno_{categoria_key}"):
            if guardar_minutos_entreno_en_disco(categoria_key, minutos_entreno):
                st.toast("Minutos de entreno guardados ✅")
            else:
                st.toast("No se pudo guardar ❌")

vista_key = st.session_state["vista_key"]
minutos_partido_guardados = cargar_minutos_partido_guardados(categoria_key)

# calcular sRPE: entreno usa minutos globales, partido usa minutos guardados por jugador+partido
df_sesiones_todas = df[df["tipo"].isin(["ENTRENO", "PARTIDO"])].copy()


def _calcular_srpe(r):
    if r["rpe"] is None:
        return None
    if r["tipo"] == "ENTRENO":
        return r["rpe"] * minutos_entreno
    mins = minutos_partido_guardados.get(f"{r['idJugador']}|{r['fecha']}")
    return None if mins is None else r["rpe"] * mins


df_sesiones_todas["srpe"] = df_sesiones_todas.apply(_calcular_srpe, axis=1)
df_sesiones = df_sesiones_todas.dropna(subset=["srpe"])  # solo registros con carga calculable
timestamp_ref = df["timestamp"].max()

# ============================================================
# FILTROS (Mes -> Semana -> Día en cascada)
# ============================================================
meses_disponibles = sorted(df["mes"].unique(), key=lambda m: NOMBRES_MESES.index(m))
with st.container(border=True, key="filtros_box"):
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        mes_sel = st.selectbox("Mes", ["TODOS"] + meses_disponibles, key=f"mes_sel_{categoria_key}")
    df_para_semanas = df if mes_sel == "TODOS" else df[df["mes"] == mes_sel]
    semanas_disponibles = ordenar_semanas_desc(df_para_semanas["semana"].unique().tolist())
    with col_f2:
        semana_sel = st.selectbox("Semana", ["TODOS"] + semanas_disponibles, key=f"semana_sel_{categoria_key}")
    df_para_dias = df_para_semanas if semana_sel == "TODOS" else df_para_semanas[df_para_semanas["semana"] == semana_sel]
    dias_disponibles = sorted(
        df_para_dias["fecha"].unique(), key=lambda d: pd.to_datetime(d, dayfirst=True), reverse=True
    )
    with col_f3:
        dia_sel = st.selectbox(
            "Día",
            ["TODOS"] + dias_disponibles,
            key=f"dia_sel_{categoria_key}",
            help="Elige un día concreto para ver TODOS los registros de ese día por separado "
                 "(útil si hubo doble sesión y un jugador respondió 2 veces).",
        )

if vista_key == "wellness":
    df_vista = df[df["tipo"] == "WELLNESS"].copy()
elif vista_key == "rpe_entreno":
    df_vista = df_sesiones[df_sesiones["tipo"] == "ENTRENO"].copy()
else:
    df_vista = df_sesiones_todas[df_sesiones_todas["tipo"] == "PARTIDO"].copy()
    df_vista["tiene_minutos"] = df_vista.apply(
        lambda r: f"{r['idJugador']}|{r['fecha']}" in minutos_partido_guardados, axis=1
    )

if mes_sel != "TODOS":
    df_vista = df_vista[df_vista["mes"] == mes_sel]
if semana_sel != "TODOS":
    df_vista = df_vista[df_vista["semana"] == semana_sel]
if dia_sel != "TODOS":
    df_vista = df_vista[df_vista["fecha"] == dia_sel]

# ============================================================
# ROSTER
# - Si no hay un día concreto seleccionado: 1 fila por jugador (su registro más reciente).
# - Si hay un día concreto seleccionado: se muestran TODOS los registros de ese día,
#   incluidos los casos de doble sesión (2 registros del mismo jugador el mismo día).
# ============================================================
if dia_sel == "TODOS":
    if not df_vista.empty:
        idx_ultimo = df_vista.groupby("idJugador")["timestamp"].idxmax()
        roster = df_vista.loc[idx_ultimo].copy()
    else:
        roster = df_vista.copy()
else:
    roster = df_vista.sort_values("timestamp").copy()
    if not roster.empty:
        roster["hora"] = roster["timestamp"].dt.strftime("%H:%M")

acwr_vals, color_vals = [], []
for _, jrow in roster.iterrows():
    hist = df_sesiones[df_sesiones["idJugador"] == jrow["idJugador"]]
    acwr, color = calcular_acwr(hist, timestamp_ref)
    acwr_vals.append(acwr)
    color_vals.append(color)
roster["acwr"] = acwr_vals
roster["colorRiesgo"] = color_vals
roster["disponibilidad"] = roster["idJugador"].map(lambda i: estados.get(i, {}).get("disponibilidad", "DISPONIBLE"))
roster["molestias_estado"] = roster["idJugador"].map(lambda i: estados.get(i, {}).get("molestias", "Sin molestias"))
orden_riesgo = {"rojo": 0, "amarillo": 1, "verde": 2}
roster["orden"] = roster["colorRiesgo"].map(orden_riesgo)
roster = roster.sort_values("orden")

# ============================================================
# KPIs
# ============================================================
disponibles = int((roster["disponibilidad"] == "DISPONIBLE").sum())
bajas = roster.shape[0] - disponibles
alertas_rojo = int((roster["colorRiesgo"] == "rojo").sum())

if vista_key == "wellness":
    label_kpi1, valor_kpi1 = "Registros de Wellness", f"{roster.shape[0]} Reg."
else:
    total = df_vista.shape[0]
    con_rpe = int(df_vista["rpe"].notna().sum())
    pct = round(con_rpe / total * 100) if total > 0 else 0
    label_kpi1, valor_kpi1 = "Tasa de Respuesta RPE", f"{pct}%"

with st.container(border=True, key="kpi_box"):
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        render_kpi(label_kpi1, valor_kpi1)
    with k2:
        render_kpi("Disponibles", disponibles, "#22c55e")
    with k3:
        render_kpi("No disponible / Bajas", bajas, "#ef4444")
    with k4:
        if vista_key == "wellness" and "wellness_score" in roster.columns:
            media_w_serie = roster["wellness_score"].dropna()
            if not media_w_serie.empty:
                media_w = media_w_serie.mean()
                render_kpi("Media Wellness Grupal", f"{media_w:.1f}", color_escala_1_5(media_w))
            else:
                render_kpi("Media Wellness Grupal", "—")
        else:
            rpe_medio_serie = df_vista["rpe"].dropna() if "rpe" in df_vista.columns else pd.Series(dtype=float)
            if not rpe_medio_serie.empty:
                media_rpe = rpe_medio_serie.mean()
                render_kpi("RPE Medio", f"{media_rpe:.1f}", color_rpe(media_rpe))
            else:
                render_kpi("RPE Medio", "—")
    with k5:
        render_kpi("Alertas Críticas ACWR", alertas_rojo, "#ef4444")

st.divider()

# ============================================================
# ROSTER + FICHA INDIVIDUAL
# ============================================================
col_izq, col_der = st.columns([5, 7])
emoji_riesgo = {"rojo": "🔴", "amarillo": "🟡", "verde": "🟢"}
jugador_sel_id, fila_jugador = None, None
fig_evolucion_individual = None

with col_izq:
    render_section_title("👥 Monitoreo de Plantilla")
    if roster.empty:
        st.info("Sin registros para el filtro activo.")
    else:
        indices_disponibles = roster.index.tolist()
        if "jugador_sel_idx" not in st.session_state or st.session_state["jugador_sel_idx"] is None:
            st.session_state["jugador_sel_idx"] = indices_disponibles[0]
        elif st.session_state["jugador_sel_idx"] not in indices_disponibles:
            st.session_state["jugador_sel_idx"] = indices_disponibles[0]
        with st.container(border=True, key="panel_monitoreo"):
            col_buscar, col_borrar = st.columns([3, 1])
            with col_buscar:
                busqueda = st.text_input(
                    "Buscar", placeholder="🔍 Buscar jugador por nombre...", label_visibility="collapsed", key="buscar_input"
                )
            with col_borrar:
                if st.button("✕ Borrar", use_container_width=True, key="borrar_sel"):
                    st.session_state["jugador_sel_idx"] = None
                    st.rerun()
            roster_visible = roster[roster["nombre"].str.contains(busqueda, case=False, na=False, regex=False)] if busqueda else roster
            with st.container(height=520, key="roster_scroll"):
                if roster_visible.empty:
                    st.caption("Ningún jugador coincide con la búsqueda.")
                for idx_fila, row in roster_visible.iterrows():
                    es_actual = idx_fila == st.session_state["jugador_sel_idx"]
                    with st.container(border=True):
                        cc1, cc2, cc3 = st.columns([1, 5, 2])
                        with cc1:
                            st.markdown(f"<div style='font-size:1.15rem; text-align:center'>{emoji_riesgo[row['colorRiesgo']]}</div>", unsafe_allow_html=True)
                        with cc2:
                            prefijo = "▶ " if es_actual else ""
                            st.markdown(
                                f"<div style='font-size:0.82rem; font-weight:700; color:#f1f5f9; line-height:1.3;'>{prefijo}[{row['idJugador']}] {row['nombre']}</div>",
                                unsafe_allow_html=True,
                            )
                            sub_fecha = row["hora"] if dia_sel != "TODOS" else row["fecha"]
                            if vista_key == "wellness":
                                val_dia = row.get("wellness_score")
                                color_dia = color_escala_1_5(val_dia)
                                etiqueta_dia = "Wellness"
                                val_txt = f"{val_dia:g}" if val_dia is not None else "—"
                            elif vista_key == "rpe_partido" and not row.get("tiene_minutos", False):
                                color_dia = "#ef4444"
                                etiqueta_dia = ""
                                val_txt = "No convocado"
                            else:
                                val_dia = row.get("rpe")
                                color_dia = color_rpe(val_dia)
                                etiqueta_dia = "RPE"
                                val_txt = f"{val_dia:g}" if val_dia is not None else "—"
                                if vista_key == "rpe_entreno":
                                    val_txt += f" · {minutos_entreno} min"
                                elif vista_key == "rpe_partido":
                                    mins_tarjeta = minutos_partido_guardados.get(f"{row['idJugador']}|{row['fecha']}")
                                    if mins_tarjeta is not None:
                                        val_txt += f" · {mins_tarjeta} min"
                            st.markdown(
                                f"<div style='font-size:0.65rem; color:#9ca3af; line-height:1.4;'>{sub_fecha} · "
                                f"<span style='color:{color_dia}; font-weight:700;'>{etiqueta_dia} {val_txt}</span></div>",
                                unsafe_allow_html=True,
                            )
                        with cc3:
                            st.markdown(
                                f"<div style='font-size:0.6rem; color:#9ca3af; text-align:right;'>ACWR</div>"
                                f"<div style='font-size:0.9rem; font-weight:800; text-align:right;'>{row['acwr']}</div>",
                                unsafe_allow_html=True,
                            )
                        if es_actual:
                            st.markdown("<span style='color:#10b981; font-weight:700; font-size:0.7rem'>✓ Seleccionado</span>", unsafe_allow_html=True)
                        else:
                            if st.button("Ver ficha →", key=f"verficha_{categoria_key}_{idx_fila}", use_container_width=True):
                                st.session_state["jugador_sel_idx"] = idx_fila
                                st.rerun()
        idx_sel = st.session_state["jugador_sel_idx"]
        fila_jugador = roster.loc[idx_sel] if idx_sel is not None else None
        jugador_sel_id = fila_jugador["idJugador"] if fila_jugador is not None else None

    # ============================================================
    # MOLESTIAS — jugadores con dolor persistente (independiente de los filtros de arriba)
    # ============================================================
    filas_molestia = []
    for id_j in df["idJugador"].unique():
        hist_jugador = df[df["idJugador"] == id_j].sort_values("timestamp")
        racha, texto_mol = calcular_racha_molestias(hist_jugador)
        if racha > 0:
            nombre_j = hist_jugador.iloc[-1]["nombre"]
            if "doms" in hist_jugador.columns:
                doms_serie = hist_jugador.loc[hist_jugador["tipo"] == "WELLNESS", "doms"].dropna()
                doms_val = doms_serie.iloc[-1] if not doms_serie.empty else None
            else:
                doms_val = None
            filas_molestia.append({"id": id_j, "nombre": nombre_j, "molestia": texto_mol, "racha": racha, "doms": doms_val})
    st.markdown(
        f"<div style='font-size:1.15rem; font-weight:900; color:#fca5a5; "
        f"border-left:5px solid #ef4444; padding-left:10px; margin:1rem 0 0.5rem 0;'>"
        f"⚠️ MOLESTIAS ACTIVAS ({len(filas_molestia)})</div>",
        unsafe_allow_html=True,
    )
    with st.expander("Ver jugadores con dolor persistente", expanded=False):
        if not filas_molestia:
            st.markdown("<div style='font-size:0.95rem; color:#4ade80; font-weight:700;'>Ningún jugador reporta molestias activas ahora mismo. 🎉</div>", unsafe_allow_html=True)
        else:
            filas_molestia.sort(key=lambda f: f["racha"], reverse=True)
            for f in filas_molestia:
                with st.container(border=True):
                    mc1, mc2, mc3 = st.columns([3, 1.3, 1.3])
                    with mc1:
                        st.markdown(f"<div style='font-weight:800; color:#f1f5f9; font-size:1.1rem;'>[{f['id']}] {f['nombre']}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div style='font-size:0.9rem; color:#fb923c; font-weight:600; margin-top:2px;'>🩹 {f['molestia']}</div>", unsafe_allow_html=True)
                    with mc2:
                        color_racha = "#facc15" if f["racha"] <= 2 else "#ef4444"
                        render_kpi("Días seguidos", f["racha"], color_racha)
                    with mc3:
                        render_kpi("DOMS", f["doms"] if f["doms"] is not None else "—", color_escala_1_5(f["doms"]))

with col_der:
    render_section_title("🩺 Ficha Individual")
    if fila_jugador is None:
        st.info("Selecciona un futbolista del roster para ver su ficha.")
    else:
      with st.container(border=True, key="panel_ficha"):
        etiquetas_color = {"rojo": "Pico de Estrés (Peligro)", "amarillo": "Precaución", "verde": "Sweet Spot (Adaptación)"}
        with st.container(border=True):
            st.markdown(
                f"<div style='font-size:1.5rem; font-weight:900; color:#ffffff; line-height:1.2;'>{fila_jugador['nombre']}</div>",
                unsafe_allow_html=True,
            )
            extra_min = ""
            if vista_key == "rpe_entreno":
                extra_min = f" · {minutos_entreno} min"
            elif vista_key == "rpe_partido":
                mins_ficha = minutos_partido_guardados.get(f"{jugador_sel_id}|{fila_jugador['fecha']}")
                if mins_ficha is not None:
                    extra_min = f" · {mins_ficha} min jugados"
            st.caption(f"CÓDIGO DE REGISTRO: {jugador_sel_id} · Último registro: {fila_jugador['fecha']}{extra_min}")
            st.markdown(
                f"**ACWR: {fila_jugador['acwr']}** {emoji_riesgo[fila_jugador['colorRiesgo']]} "
                f"— {etiquetas_color[fila_jugador['colorRiesgo']]}"
            )
        with st.container(border=True):
            c1, c2 = st.columns(2)
            with c1:
                color_disp = "#22c55e" if fila_jugador["disponibilidad"] == "DISPONIBLE" else "#ef4444"
                render_kpi("Disponibilidad", fila_jugador["disponibilidad"], color_disp)
            with c2:
                mol_val = fila_jugador["molestias_estado"]
                color_mol = "#fb923c" if mol_val and mol_val != "Sin molestias" else "#9ca3af"
                render_kpi("Molestias", mol_val, color_mol)
        if vista_key == "wellness":
            st.markdown("**Detalle Wellness de hoy**")
            tiene_periodo = "periodo" in fila_jugador.index and pd.notna(fila_jugador.get("periodo"))
            columnas_wellness = st.columns(6 if tiene_periodo else 5)
            cw1, cw2, cw3, cw4, cw5 = columnas_wellness[:5]
            with cw1:
                with st.container(border=True):
                    render_kpi("Fatiga", fila_jugador.get("fatiga") if fila_jugador.get("fatiga") is not None else "—", color_escala_1_5(fila_jugador.get("fatiga")))
            with cw2:
                with st.container(border=True):
                    render_kpi("Sueño", fila_jugador.get("sueno") if fila_jugador.get("sueno") is not None else "—", color_escala_1_5(fila_jugador.get("sueno")))
            with cw3:
                with st.container(border=True):
                    render_kpi("Estrés", fila_jugador.get("estres") if fila_jugador.get("estres") is not None else "—", color_escala_1_5(fila_jugador.get("estres")))
            with cw4:
                with st.container(border=True):
                    render_kpi("DOMS", fila_jugador.get("doms") if fila_jugador.get("doms") is not None else "—", color_escala_1_5(fila_jugador.get("doms")))
            with cw5:
                with st.container(border=True):
                    orina_val = fila_jugador.get("orina")
                    color_orina = "#ef4444" if orina_val is not None and orina_val >= 9 else "#f1f5f9"
                    render_kpi("Orina", orina_val if orina_val is not None else "—", color_orina)
                    if orina_val is not None and orina_val >= 9:
                        st.markdown("<div style='text-align:center; color:#ef4444; font-size:0.65rem; font-weight:700'>⚠️ Posible sangre</div>", unsafe_allow_html=True)
            if tiene_periodo:
                with columnas_wellness[5]:
                    with st.container(border=True):
                        render_kpi("Período", fila_jugador.get("periodo") or "—", "#f472b6")
        elif vista_key == "rpe_partido":
            clave_partido = f"{jugador_sel_id}|{fila_jugador['fecha']}"
            tiene_min = fila_jugador.get("tiene_minutos", False)
            with st.container(border=True):
                st.markdown(f"**⚽ Minutos jugados — Partido del {fila_jugador['fecha']}**")
                if not tiene_min:
                    st.markdown("<span style='color:#ef4444; font-weight:800;'>🔴 No convocado (sin minutos guardados)</span>", unsafe_allow_html=True)
                cmp1, cmp2 = st.columns([2, 1])
                with cmp1:
                    valor_previo = int(minutos_partido_guardados.get(clave_partido, 0))
                    minutos_este_partido = st.number_input(
                        "Minutos jugados", min_value=0, max_value=130, value=valor_previo, step=5,
                        label_visibility="collapsed", key=f"min_p_{categoria_key}_{clave_partido}",
                    )
                with cmp2:
                    if st.button("💾 Guardar", key=f"guardar_p_{categoria_key}_{clave_partido}", use_container_width=True):
                        if guardar_minutos_partido_en_disco(categoria_key, jugador_sel_id, fila_jugador["fecha"], minutos_este_partido):
                            st.toast("Minutos del partido guardados ✅")
                            st.rerun()
                        else:
                            st.toast("No se pudo guardar ❌")
            st.markdown("**Detalle del último registro**")
            cr1, cr2 = st.columns(2)
            with cr1:
                with st.container(border=True):
                    rpe_val = fila_jugador.get("rpe")
                    render_kpi("RPE", rpe_val if rpe_val is not None else "—", color_rpe(rpe_val))
            with cr2:
                with st.container(border=True):
                    rend_val = fila_jugador.get("rendimiento")
                    render_kpi("Rendimiento (1-10)", rend_val if rend_val is not None else "—", "#f1f5f9")
        else:
            st.markdown("**Detalle del último registro**")
            cr1, cr2 = st.columns(2)
            with cr1:
                with st.container(border=True):
                    rpe_val = fila_jugador.get("rpe")
                    render_kpi("RPE", rpe_val if rpe_val is not None else "—", color_rpe(rpe_val))
            with cr2:
                with st.container(border=True):
                    rend_val = fila_jugador.get("rendimiento")
                    render_kpi("Rendimiento (1-10)", rend_val if rend_val is not None else "—", "#f1f5f9")
        with st.container(border=True):
            st.markdown("**Evolución de la Carga (sRPE, últimos 7 días)**")
            leyenda_ua = "".join(
                f"<span style='display:inline-flex; align-items:center; margin-right:10px; font-size:0.68rem; color:#cbd5e1;'>"
                f"<span style='width:9px; height:9px; border-radius:50%; background:{c}; display:inline-block; margin-right:4px;'></span>{t}</span>"
                for c, t in [
                    ("#16a34a", "0-200 Regenerativo"),
                    ("#4ade80", "200-400 Baja"),
                    ("#facc15", "400-600 Moderada"),
                    ("#fb923c", "600-800 Alta"),
                    ("#ef4444", "800-1000 Muy Alta"),
                    ("#991b1b", ">1000 Riesgo"),
                ]
            )
            st.markdown(f"<div style='margin-bottom:6px; line-height:1.8;'>{leyenda_ua}</div>", unsafe_allow_html=True)
            historial = df_sesiones[
                (df_sesiones["idJugador"] == jugador_sel_id)
                & (df_sesiones["timestamp"] >= timestamp_ref - pd.Timedelta(days=6))
                & (df_sesiones["timestamp"] <= timestamp_ref)
            ].sort_values("timestamp")
            if historial.empty:
                st.caption("Sin sesiones de Entreno/Partido en los últimos 7 días para este jugador.")
            else:
                colores_puntos = [color_carga(v) for v in historial["srpe"]]
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=historial["fecha"], y=historial["srpe"], mode="lines+markers",
                    line=dict(color="#64748b", width=2),
                    marker=dict(color=colores_puntos, size=13, line=dict(color="#0f172a", width=1.5)),
                    fill="tozeroy", fillcolor="rgba(100,116,139,0.08)",
                    hovertemplate="Carga: %{y:.0f} UA<extra></extra>",
                ))
                fig.update_layout(
                    template="plotly_dark", height=260, margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
                    xaxis=dict(gridcolor="rgba(255,255,255,0.05)", zeroline=False, linecolor="rgba(255,255,255,0.1)"),
                    yaxis=dict(gridcolor="rgba(255,255,255,0.03)", zeroline=False, linecolor="rgba(255,255,255,0.1)", nticks=4),
                )
                fig_evolucion_individual = fig
                st.plotly_chart(fig, use_container_width=True)

st.divider()

# ============================================================
# CARGA POR DÍA DE LA SEMANA — Entreno vs Partido
# ============================================================
fig_semana = None
subtitulo_semana_pdf = f"Media del equipo — {CATEGORIA}"
render_section_title("📊 Carga por Día de la Semana — Entrenamiento vs Partido")
with st.container(border=True):
    df_chart = df_sesiones.copy()
    if mes_sel != "TODOS":
        df_chart = df_chart[df_chart["mes"] == mes_sel]
    if df_chart.empty:
        st.caption("Sin datos de carga para este filtro.")
    else:
        df_chart["dia_semana"] = df_chart["timestamp"].dt.dayofweek.map(lambda d: DIAS_SEMANA[d])
        if jugador_sel_id:
            df_chart_jugador = df_chart[df_chart["idJugador"] == jugador_sel_id]
            resumen = df_chart_jugador.groupby(["dia_semana", "tipo"])["srpe"].sum().unstack(fill_value=0)
            subtitulo = f"Individual — {fila_jugador['nombre']}"
        else:
            resumen = df_chart.groupby(["dia_semana", "tipo"])["srpe"].mean().unstack(fill_value=0)
            subtitulo = f"Media del equipo — {CATEGORIA}"
        st.caption(f"Análisis de carga para: {subtitulo}")
        subtitulo_semana_pdf = subtitulo
        resumen = resumen.reindex(DIAS_SEMANA).fillna(0)
        fig_semana = go.Figure()
        if "ENTRENO" in resumen.columns:
            fig_semana.add_trace(go.Bar(
                name="Entrenamiento", x=resumen.index, y=resumen["ENTRENO"], marker_color="#10b981",
                hovertemplate="%{x}<br>Entrenamiento: %{y:.0f} UA<extra></extra>",
            ))
        if "PARTIDO" in resumen.columns:
            fig_semana.add_trace(go.Bar(
                name="Partido", x=resumen.index, y=resumen["PARTIDO"], marker_color="#ef4444",
                hovertemplate="%{x}<br>Partido: %{y:.0f} UA<extra></extra>",
            ))
        fig_semana.update_layout(
            template="plotly_dark", height=280, barmode="group", bargap=0.3, bargroupgap=0.15,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            xaxis=dict(showgrid=False, linecolor="rgba(255,255,255,0.15)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.04)", zeroline=False, nticks=4, showticklabels=True),
        )
        st.plotly_chart(fig_semana, use_container_width=True)

# ============================================================
# EXPORTAR INFORME PDF — se rellena aquí, pero se muestra arriba de todo
# (en pdf_placeholder, creado justo debajo del selector de categoría).
# ============================================================
if vista_key == "wellness" and "wellness_score" in roster.columns:
    _serie_media_pdf = roster["wellness_score"].dropna()
    media_label_pdf = "Media Wellness Grupal"
    media_txt_pdf = f"{_serie_media_pdf.mean():.1f}" if not _serie_media_pdf.empty else "—"
else:
    _serie_media_pdf = df_vista["rpe"].dropna() if "rpe" in df_vista.columns else pd.Series(dtype=float)
    media_label_pdf = "RPE Medio"
    media_txt_pdf = f"{_serie_media_pdf.mean():.1f}" if not _serie_media_pdf.empty else "—"

if vista_key == "wellness":
    columnas_tabla_pdf = ["ID", "Nombre", "Wellness", "ACWR", "Disponibilidad", "Molestias"]
else:
    columnas_tabla_pdf = ["ID", "Nombre", "RPE", "Rendimiento", "ACWR", "Disponibilidad", "Molestias"]

filas_tabla_pdf = []
for _, row_pdf in roster.sort_values("nombre").iterrows():
    molestias_txt_pdf = row_pdf.get("molestias_estado") or "Sin molestias"
    if vista_key == "wellness":
        val_wellness_pdf = row_pdf.get("wellness_score")
        filas_tabla_pdf.append([
            str(row_pdf.get("idJugador", "")),
            str(row_pdf.get("nombre", "")),
            f"{val_wellness_pdf:.1f}" if pd.notna(val_wellness_pdf) else "—",
            str(row_pdf.get("acwr", "—")),
            str(row_pdf.get("disponibilidad", "—")),
            molestias_txt_pdf,
        ])
    else:
        val_rpe_pdf = row_pdf.get("rpe")
        val_rend_pdf = row_pdf.get("rendimiento")
        filas_tabla_pdf.append([
            str(row_pdf.get("idJugador", "")),
            str(row_pdf.get("nombre", "")),
            f"{val_rpe_pdf:.0f}" if pd.notna(val_rpe_pdf) else "—",
            f"{val_rend_pdf:.0f}" if pd.notna(val_rend_pdf) else "—",
            str(row_pdf.get("acwr", "—")),
            str(row_pdf.get("disponibilidad", "—")),
            molestias_txt_pdf,
        ])

jugador_info_pdf = None
if fila_jugador is not None:
    if vista_key == "wellness":
        detalle_partes_pdf = []
        for etiqueta_pdf, campo_pdf in [("Fatiga", "fatiga"), ("Sueño", "sueno"), ("Estrés", "estres"), ("DOMS", "doms"), ("Orina", "orina")]:
            v_pdf = fila_jugador.get(campo_pdf)
            detalle_partes_pdf.append(f"{etiqueta_pdf}: {v_pdf:g}" if pd.notna(v_pdf) else f"{etiqueta_pdf}: —")
        if "periodo" in fila_jugador.index and pd.notna(fila_jugador.get("periodo")):
            detalle_partes_pdf.append(f"Período: {fila_jugador.get('periodo')}")
        detalle_texto_pdf = " · ".join(detalle_partes_pdf)
    else:
        rpe_v_pdf = fila_jugador.get("rpe")
        rend_v_pdf = fila_jugador.get("rendimiento")
        detalle_texto_pdf = (
            (f"RPE: {rpe_v_pdf:g}" if pd.notna(rpe_v_pdf) else "RPE: —")
            + " · "
            + (f"Rendimiento: {rend_v_pdf:g}" if pd.notna(rend_v_pdf) else "Rendimiento: —")
        )
    jugador_info_pdf = {
        "nombre": fila_jugador.get("nombre", ""),
        "id": jugador_sel_id,
        "acwr": fila_jugador.get("acwr", "—"),
        "disponibilidad": fila_jugador.get("disponibilidad", "—"),
        "molestias": fila_jugador.get("molestias_estado") or "Sin molestias",
        "detalle": detalle_texto_pdf,
    }

filtros_texto_pdf = f"Mes: {mes_sel} · Semana: {semana_sel} · Día: {dia_sel}"
vista_label_pdf = {"wellness": "Wellness", "rpe_entreno": "RPE Entrenamiento", "rpe_partido": "RPE Partido"}[vista_key]
firma_actual_pdf = (categoria_key, vista_key, mes_sel, semana_sel, dia_sel, jugador_sel_id)

if "pdf_bytes" not in st.session_state:
    st.session_state["pdf_bytes"] = None
    st.session_state["pdf_firma"] = None

with pdf_placeholder:
    col_pdf_btn, col_pdf_dl, col_pdf_info = st.columns([2, 2, 5])
    with col_pdf_btn:
        if st.button("📄 Generar informe PDF", use_container_width=True, key="btn_generar_pdf"):
            with st.spinner("Generando informe PDF..."):
                kpis_pdf = [
                    (label_kpi1, str(valor_kpi1)),
                    ("Disponibles", str(disponibles)),
                    ("Bajas", str(bajas)),
                    (media_label_pdf, media_txt_pdf),
                    ("Alertas ACWR", str(alertas_rojo)),
                ]
                st.session_state["pdf_bytes"] = generar_pdf_informe(
                    categoria_label=CATEGORIA,
                    vista_label=vista_label_pdf,
                    filtros_texto=filtros_texto_pdf,
                    kpis=kpis_pdf,
                    columnas_tabla=columnas_tabla_pdf,
                    filas_tabla=filas_tabla_pdf,
                    jugador_info=jugador_info_pdf,
                    fig_evolucion=fig_evolucion_individual,
                    fig_semana=fig_semana,
                    subtitulo_semana=subtitulo_semana_pdf,
                )
                st.session_state["pdf_firma"] = firma_actual_pdf
    with col_pdf_dl:
        if st.session_state["pdf_bytes"] is not None and st.session_state["pdf_firma"] == firma_actual_pdf:
            nombre_pdf = f"informe_{categoria_key}_{vista_key}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.pdf"
            st.download_button(
                "⬇️ Descargar PDF", data=st.session_state["pdf_bytes"], file_name=nombre_pdf,
                mime="application/pdf", use_container_width=True, key="btn_descargar_pdf",
            )
        elif st.session_state["pdf_bytes"] is not None:
            st.caption("Los filtros cambiaron: vuelve a generar el PDF.")
    with col_pdf_info:
        st.caption("Exporta la categoría, vista y filtros (Mes/Semana/Día) seleccionados ahora mismo: tabla de plantilla, ficha del jugador elegido (si hay) y gráficos.")
