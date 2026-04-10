import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --------------------------------------------------
# CONFIGURACIÓN GENERAL
# --------------------------------------------------
st.set_page_config(
    page_title="Condiciones laborales de mujeres jornaleras agrícolas | ENOE 2023–2025",
    layout="wide"
)

# --------------------------------------------------
# ENCABEZADO Y FUENTE
# --------------------------------------------------
st.title("Condiciones laborales de las mujeres jornaleras agrícolas en México")

st.caption(
    """
    **Fuente:** Encuesta Nacional de Ocupación y Empleo (ENOE), INEGI.  
    Años de referencia: 2023, 2024 y 2025 (tercer trimestre).  
    Ingresos expresados en **pesos corrientes** o **pesos constantes de 2025**.  
    Elaboración: Fundar, Centro de Análisis e Investigación.
    """
)

# --------------------------------------------------
# RUTA BASE DE LOS DATOS
# --------------------------------------------------
from pathlib import Path

_ROOT = Path(__file__).parent
_ENOE = _ROOT / "Datos" / "ENOE"
_SAL_MIN = _ROOT / "Datos" / "Salario Minimo"
_ENT = _ROOT / "Datos" / "Entidades"

# --------------------------------------------------
# CARGA DE DATOS (CACHÉ)
# --------------------------------------------------
@st.cache_data
def cargar_tabla_nacional():
    return pd.read_csv(
        _ENOE / "tabla_nacional_jornaleria_agricola_2023a2025_final_precios_constantes_2025.csv"
    )

@st.cache_data
def cargar_tabla_composicion():
    return pd.read_csv(
        _ENOE / "tabla_composicion_agro_sexo_jornaleria_2023a2025_final.csv"
    )

@st.cache_data
def cargar_tabla_estatal():
    return pd.read_csv(
        _ENOE / "tabla_estatal_mujeres_jornaleras_agricolas_2023a2025_final_precios_constantes_2025.csv"
    )

@st.cache_data
def cargar_salario_minimo():
    return pd.read_csv(
        _SAL_MIN / "CONASAMI_Salario_Minimo_diario_mensual.csv"
    )

@st.cache_data
def cargar_catalogo_entidades():
    return pd.read_csv(
        _ENT / "ent.csv"
    )

tabla_nacional = cargar_tabla_nacional()
tabla_composicion = cargar_tabla_composicion()
tabla_estatal = cargar_tabla_estatal()
sal_min = cargar_salario_minimo()
cat_ent = cargar_catalogo_entidades()
cat_ent["ent"] = cat_ent["ent"].astype(int)

# --------------------------------------------------
# FILTROS GLOBALES
# --------------------------------------------------
anio_sel = st.selectbox(
    "Año de referencia",
    sorted(tabla_nacional["anio"].unique())
)

tabla_nacional_sel = tabla_nacional[tabla_nacional["anio"] == anio_sel]
tabla_composicion_sel = tabla_composicion[tabla_composicion["anio"] == anio_sel]
tabla_estatal_sel = tabla_estatal[tabla_estatal["anio"] == anio_sel]

tipo_ingreso = st.radio(
    "Tipo de ingreso",
    ["Pesos constantes 2025", "Pesos corrientes"],
    horizontal=True
)

# Selección dinámica de columnas según tipo de ingreso
col_ingreso_enoe = (
    "ingreso_mediana_real_2025"
    if tipo_ingreso == "Pesos constantes 2025"
    else "ingreso_mediana"
)

col_sal_min = (
    "salario_mensual_real_2025"
    if tipo_ingreso == "Pesos constantes 2025"
    else "salario_minimo_mensual"
)



# --------------------------------------------------
# MÉTRICAS NACIONALES (AÑO SELECCIONADO)
# --------------------------------------------------
fila_mujeres = tabla_nacional_sel[
    tabla_nacional_sel["grupo"] == "Mujeres jornaleras agrícolas"
].iloc[0]

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric(
    f"Ingreso laboral mensual (mediana, {tipo_ingreso})",
    f"${fila_mujeres[col_ingreso_enoe]:,.0f}"
)
c2.metric(
    "Horas trabajadas (promedio)",
    f"{fila_mujeres['horas_media']:.1f}"
)
c3.metric(
    "Con sobrejornada",
    f"{fila_mujeres['prop_sobrejornada']:.1%}"
)
c4.metric(
    "Sin seguridad social",
    f"{fila_mujeres['prop_sin_ss']:.1%}"
)
c5.metric(
    "Población estimada de mujeres jornaleras agrícolas",
    f"{int(fila_mujeres['poblacion']):,}"
)

# ==================================================
# SECCIÓN 2 — COMPOSICIÓN INTERSECCIONAL
# ==================================================
st.header(
    f"¿Qué peso tienen las mujeres jornaleras dentro del empleo agropecuario en {anio_sel} "
    "y cómo se distribuyen por sexo y tipo de empleo?"
)

df_mekko = tabla_composicion_sel.copy()

fig = go.Figure()

PALETA = {
    "Hombres jornaleros":     "#003f5c",
    "Hombres no jornaleros":  "#7a9cc6",
    "Mujeres jornaleras":     "#0b5d1e",
    "Mujeres no jornaleras":  "#4caf50",
}
colores = df_mekko["grupo_agro_sexo_jornal"].map(PALETA).fillna("#9e9e9e").tolist()

fig.add_trace(
    go.Bar(
        x=df_mekko["porcentaje"],
        y=["Empleo agropecuario"] * len(df_mekko),
        orientation="h",
        text=df_mekko["grupo_agro_sexo_jornal"],
        customdata=df_mekko["porcentaje"],
        texttemplate="%{text}<br>%{customdata:.1%}",
        hovertemplate="<b>%{text}</b><br>Participación: %{customdata:.1%}<extra></extra>",
        marker_color=colores,
    )
)

fig.update_layout(
    xaxis_title="Participación porcentual en el empleo agropecuario",
    xaxis=dict(tickformat=".0%"),
    yaxis_visible=False,
    showlegend=False,
    height=260,
    margin=dict(l=20, r=20, t=20, b=20)
)

st.plotly_chart(fig, use_container_width=True)

# ==================================================
# SECCIÓN 1 — CONTEXTO NACIONAL
# ==================================================
st.header(
    f"¿Cuál es la situación laboral de referencia de las mujeres jornaleras agrícolas en {anio_sel}?"
)

st.markdown(
    """
    Esta sección presenta indicadores nacionales descriptivos,
    construidos con diseño muestral complejo.
    Funcionan como **marco de referencia anual** (tercer trimestre),
    no como umbrales normativos.
    """
)

# --------------------------------------------------
# SUBSECCIÓN — INGRESO VS SALARIO MÍNIMO (SLOPEGRAPH)
# --------------------------------------------------
st.subheader("Ingreso laboral mediano y referencia al salario mínimo (2023–2025)")

df_slope = (
    tabla_nacional
    .query("grupo == 'Mujeres jornaleras agrícolas'")
    [["anio", col_ingreso_enoe]]
    .merge(
        sal_min[["anio", col_sal_min]],
        on="anio",
        how="left"
    )
    .sort_values("anio")
)

fig_slope = go.Figure()

fig_slope.add_trace(
    go.Scatter(
        x=df_slope["anio"],
        y=df_slope[col_ingreso_enoe],
        mode="lines+markers",
        name="Ingreso mediano (ENOE)",
        line=dict(width=3, color="#0b5d1e"),
        marker=dict(size=8),
    )
)

fig_slope.add_trace(
    go.Scatter(
        x=df_slope["anio"],
        y=df_slope[col_sal_min],
        mode="lines+markers",
        name="Salario mínimo mensual equivalente",
        line=dict(width=3, dash="dot", color="#9e9e9e"),
        marker=dict(size=8),
    )
)

fig_slope.update_layout(
    xaxis_title="Año",
    yaxis_title=f"Ingreso mensual ({tipo_ingreso})",
    height=350,
    legend=dict(orientation="h", y=-0.25),
    margin=dict(l=40, r=40, t=20, b=20)
)

st.plotly_chart(fig_slope, use_container_width=True)

st.caption(
    """
    El salario mínimo diario reportado por CONASAMI se convirtió a ingreso mensual
    multiplicándolo por 30.4, conforme al criterio estadístico utilizado por INEGI.
    """
)

# --------------------------------------------------
# SUBSECCIÓN — SOBREJORNADA (SLOPEGRAPH)
# --------------------------------------------------
st.subheader("Persistencia de la sobrejornada laboral (2023–2025)")

df_sobrejornada = (
    tabla_nacional
    .query("grupo == 'Mujeres jornaleras agrícolas'")
    [["anio", "prop_sobrejornada"]]
    .sort_values("anio")
)

fig_sobre = go.Figure()

fig_sobre.add_trace(
    go.Scatter(
        x=df_sobrejornada["anio"],
        y=df_sobrejornada["prop_sobrejornada"],
        mode="lines+markers",
        name="Con sobrejornada",
        line=dict(width=3, color="#e65100"),
        marker=dict(size=8),
    )
)

fig_sobre.update_layout(
    xaxis_title="Año",
    yaxis_title="Proporción con sobrejornada",
    yaxis=dict(tickformat=".0%"),
    height=300,
    showlegend=False,
    margin=dict(l=40, r=40, t=20, b=20)
)

st.plotly_chart(fig_sobre, use_container_width=True)

st.caption(
    """
    La sobrejornada se refiere a personas que reportan trabajar más horas
    que la jornada legal. Aunque pueden observarse variaciones anuales,
    la condición persiste en el tiempo.
    """
)

# --------------------------------------------------
# SUBSECCIÓN — SEGURIDAD SOCIAL (SLOPEGRAPH)
# --------------------------------------------------
st.subheader("Persistencia de la exclusión de la seguridad social (2023–2025)")

df_seguridad = (
    tabla_nacional
    .query("grupo == 'Mujeres jornaleras agrícolas'")
    [["anio", "prop_sin_ss"]]
    .sort_values("anio")
)

fig_ss = go.Figure()

fig_ss.add_trace(
    go.Scatter(
        x=df_seguridad["anio"],
        y=df_seguridad["prop_sin_ss"],
        mode="lines+markers",
        name="Sin seguridad social",
        line=dict(width=3, color="#6a1b9a"),
        marker=dict(size=8),
    )
)

fig_ss.update_layout(
    xaxis_title="Año",
    yaxis_title="Proporción sin seguridad social",
    yaxis=dict(tickformat=".0%"),
    height=300,
    showlegend=False,
    margin=dict(l=40, r=40, t=20, b=20)
)

st.plotly_chart(fig_ss, use_container_width=True)

st.caption(
    """
    La ausencia de acceso a seguridad social constituye una forma de exclusión
    institucional. Los niveles observados se mantienen elevados a lo largo
    del periodo analizado.
    """
)



# ==================================================
# CONSTRUCCIÓN DE PERSISTENCIA TERRITORIAL (2023–2025)
# ==================================================

# Contamos, por entidad, cuántas veces aparece cada categoría
persistencia = (
    tabla_estatal
    .groupby("ent")
    .agg(
        n_anios_alta = ("precariedad_categoria", lambda x: (x == "Alta").sum()),
        n_anios_media = ("precariedad_categoria", lambda x: (x == "Media").sum()),
        n_anios_total = ("anio", "nunique")
    )
    .reset_index()
)

# Clasificación de persistencia según reglas acordadas
def clasificar_persistencia(row):
    if row["n_anios_alta"] >= 2:
        return "Alta persistente"
    elif row["n_anios_media"] >= 2:
        return "Media persistente"
    else:
        return "No persistente"

persistencia["persistencia_precariedad"] = persistencia.apply(
    clasificar_persistencia,
    axis=1
)

# Orden sugerido para lectura
orden_persistencia = [
    "Alta persistente",
    "Media persistente",
    "No persistente"
]

persistencia["persistencia_precariedad"] = pd.Categorical(
    persistencia["persistencia_precariedad"],
    categories=orden_persistencia,
    ordered=True
)

persistencia = persistencia.sort_values(
    ["persistencia_precariedad", "n_anios_alta"],
    ascending=[True, False]
)

# ==================================================
# PREPARAR DATOS PARA TABLA SEMÁFORO
# ==================================================

# Nos quedamos solo con lo necesario
base_semaforo = tabla_estatal[
    ["ent", "anio", "precariedad_categoria"]
].copy()

# Pivotear para tener un año por columna
semaforo = (
    base_semaforo
    .pivot(index="ent", columns="anio", values="precariedad_categoria")
    .reset_index()
)

# Unimos la persistencia calculada previamente
semaforo = semaforo.merge(
    persistencia[["ent", "persistencia_precariedad"]],
    on="ent",
    how="left"
)

orden_persistencia = [
    "Alta persistente",
    "Media persistente",
    "No persistente"
]

semaforo["persistencia_precariedad"] = pd.Categorical(
    semaforo["persistencia_precariedad"],
    categories=orden_persistencia,
    ordered=True
)

semaforo = semaforo.sort_values(
    ["persistencia_precariedad"]
)

def color_semaforo(val):
    if val == "Alta":
        return "background-color: #f8d7da; color: #721c24;"  # rojo suave
    elif val == "Media":
        return "background-color: #fff3cd; color: #856404;"  # amarillo suave
    elif val == "Baja":
        return "background-color: #d4edda; color: #155724;"  # verde suave
    else:
        return ""
    

# ==================================================
# SECCIÓN 4 — PERSISTENCIA TERRITORIAL DE LA PRECARIEDAD
# ==================================================
st.header(
    "¿En qué entidades federativas la precariedad laboral se presenta de forma persistente?"
)

st.markdown(
    """
    Esta sección identifica **patrones de persistencia territorial**
    en las condiciones laborales de las mujeres jornaleras agrícolas,
    a partir de la recurrencia de categorías de precariedad
    en el periodo 2023–2025.
    """
)

# --------------------------------------------------
# METRICS AGREGADAS
# --------------------------------------------------
n_alta_persistente = (
    persistencia
    .query("persistencia_precariedad == 'Alta persistente'")
    .shape[0]
)

n_media_persistente = (
    persistencia
    .query("persistencia_precariedad == 'Media persistente'")
    .shape[0]
)

n_no_persistente = (
    persistencia
    .query("persistencia_precariedad == 'No persistente'")
    .shape[0]
)

c1, c2, c3 = st.columns(3)

c1.metric(
    "Entidades con precariedad alta persistente",
    n_alta_persistente,
    help="Clasificadas como 'Alta' en al menos 2 de los 3 años (2023–2025)."
)

c2.metric(
    "Entidades con precariedad media persistente",
    n_media_persistente,
    help="Clasificadas como 'Media' en al menos 2 de los 3 años."
)

c3.metric(
    "Entidades no persistentes",
    n_no_persistente,
    help="Sin recurrencia sistemática de precariedad en el periodo analizado."
)

# --------------------------------------------------
# TABLA SEMÁFORO
# --------------------------------------------------

# 1) Base estado–año (NO renombrar aquí)
base_semaforo = tabla_estatal[
    ["ent", "anio", "precariedad_categoria"]
].copy()

# 2) Pivotear: años como columnas (ent sigue siendo la llave)
semaforo = (
    base_semaforo
    .pivot(index="ent", columns="anio", values="precariedad_categoria")
    .reset_index()
)

# 3) Unir persistencia (primer merge)
semaforo = semaforo.merge(
    persistencia[["ent", "persistencia_precariedad"]],
    on="ent",
    how="left"
)

# 4) Unir catálogo de entidades (segundo merge)
semaforo = semaforo.merge(
    cat_ent,   # ent.csv
    on="ent",
    how="left"
)

# 5) Etiquetas con íconos para persistencia
def etiqueta_persistencia(val):
    if val == "Alta persistente":
        return "🔴 Alta persistente"
    elif val == "Media persistente":
        return "🟡 Media persistente"
    else:
        return "⚪ No persistente"

semaforo["Persistencia territorial"] = (
    semaforo["persistencia_precariedad"]
    .apply(etiqueta_persistencia)
)

# 6) Ordenar para que destaque la persistencia
orden_persistencia = [
    "Alta persistente",
    "Media persistente",
    "No persistente"
]

semaforo["persistencia_precariedad"] = pd.Categorical(
    semaforo["persistencia_precariedad"],
    categories=orden_persistencia,
    ordered=True
)

semaforo = semaforo.sort_values(
    ["persistencia_precariedad"]
)

# 7) Función de color tipo semáforo por año
def color_semaforo_categoria(val):
    if val == "Alta":
        return "background-color: #f8d7da; color: #721c24;"   # rojo suave
    elif val == "Media":
        return "background-color: #fff3cd; color: #856404;"  # amarillo suave
    elif val == "Baja":
        return "background-color: #d4edda; color: #155724;"  # verde suave
    else:
        return ""

# 8) Mostrar tabla final (YA con nombres)
st.dataframe(
    semaforo[
        ["descrip", 2023, 2024, 2025, "Persistencia territorial"]
    ]
    .rename(columns={"descrip": "Entidad federativa"})
    .style
    .map(
        color_semaforo_categoria,
        subset=[2023, 2024, 2025]
    ),
    use_container_width=True
)

st.caption(
    """
    Los colores indican la categoría de precariedad laboral por entidad y año:
    verde = baja, amarillo = media, rojo = alta.
    La persistencia territorial se define a partir de la recurrencia de estas categorías en 2023–2025.
    """
)

# --------------------------------------------------
# HEATMAP ESTADOS × AÑOS (INDICADOR SELECCIONABLE)
# --------------------------------------------------
st.subheader(
    "Evolución reciente de las condiciones laborales por entidad federativa"
)

st.markdown(
    """
    El siguiente gráfico muestra la distribución territorial de **un indicador específico**
    de las condiciones laborales de las mujeres jornaleras agrícolas
    a lo largo del periodo 2023–2025.
    Cada columna corresponde a un año y cada fila a una entidad federativa.
    """
)

# --------------------------------------------------
# SELECTOR DE INDICADOR (MAPA LIMPIO)
# --------------------------------------------------
mapa_indicadores = {
    "Ingreso mediano mensual (pesos constantes 2025)": "ingreso_mediana_real_2025",
    "Proporción con sobrejornada": "prop_sobrejornada",
    "Proporción sin seguridad social": "prop_sin_ss"
}

label_sel = st.selectbox(
    "Selecciona el indicador a visualizar",
    options=list(mapa_indicadores.keys())
)

col_indicador = mapa_indicadores[label_sel]
label_indicador = label_sel

# --------------------------------------------------
# PREPARAR DATOS PARA HEATMAP
# --------------------------------------------------
heatmap_base = (
    tabla_estatal
    .merge(cat_ent, on="ent", how="left")
    [
        ["descrip", "anio", col_indicador]
    ]
    .rename(columns={"descrip": "Entidad federativa"})
)

# Pivotear: filas = estados, columnas = años
heatmap_pivot = (
    heatmap_base
    .pivot(
        index="Entidad federativa",
        columns="anio",
        values=col_indicador
    )
    .sort_index()
)

# --------------------------------------------------
# NORMALIZACIÓN GLOBAL (0–1)
# --------------------------------------------------
heatmap_norm = (
    heatmap_pivot - heatmap_pivot.min().min()
) / (
    heatmap_pivot.max().max() - heatmap_pivot.min().min()
)

# --------------------------------------------------
# CONSTRUIR HEATMAP
# --------------------------------------------------
# -----------------------------------------------
# DEFINIR ESCALA DE COLOR SEGÚN EL INDICADOR
# -----------------------------------------------
if col_indicador == "ingreso_mediana_real_2025":
    escala_color = "RdYlGn"      # verde = mejor ingreso
else:
    escala_color = "RdYlGn_r"    # rojo = mayor precariedad

fig_heatmap = go.Figure(
    data=go.Heatmap(
        z=heatmap_norm.values,
        x=heatmap_norm.columns.astype(str),
        y=heatmap_norm.index,
        colorscale=escala_color,
        colorbar=dict(title="Nivel relativo"),
        hovertemplate=(
            "Entidad: %{y}<br>"
            "Año: %{x}<br>"
            + label_indicador
            + ": %{customdata}<extra></extra>"
        ),
        customdata=heatmap_pivot.values
    )
)

fig_heatmap.update_layout(
    height=800,
    xaxis_title="Año",
    yaxis_title="Entidad federativa",
    margin=dict(l=140, r=40, t=40, b=40)
)

st.plotly_chart(fig_heatmap, use_container_width=True)

st.caption(
    """
    El color representa la posición relativa del valor del indicador
    en el conjunto de entidades y años (normalización global).
    Este gráfico es descriptivo y no implica persistencia estructural;
    dicha persistencia se analiza en la sección siguiente.
    """
)

# --------------------------------------------------
# CONCENTRACIÓN DE MUJERES JORNALERAS AGRÍCOLAS (BARRAS)
# --------------------------------------------------
st.subheader(
    f"Concentración de mujeres jornaleras agrícolas por entidad federativa ({anio_sel})"
)

st.markdown(
    """
    El gráfico muestra la **concentración relativa de mujeres jornaleras agrícolas**
    por entidad federativa en el año seleccionado.
    Se presentan únicamente las entidades con mayor población estimada
    para facilitar la lectura.
    """
)

# Preparar datos
df_barras = (
    tabla_estatal_sel
    .merge(cat_ent, on="ent", how="left")
    [["descrip", "poblacion"]]
    .rename(columns={
        "descrip": "Entidad federativa",
        "poblacion": "Mujeres jornaleras agrícolas"
    })
    .sort_values("Mujeres jornaleras agrícolas", ascending=False)
)

# Quedarnos con top 15
top_n = 32
df_top = df_barras.head(top_n)

# Gráfico de barras horizontal
fig_barras = go.Figure(
    go.Bar(
        x=df_top["Mujeres jornaleras agrícolas"],
        y=df_top["Entidad federativa"],
        orientation="h",
        marker_color="#0b5d1e"
    )
)

fig_barras.update_layout(
    height=600,
    xaxis_title="Población estimada de mujeres jornaleras agrícolas",
    yaxis_title="Entidad federativa",
    yaxis=dict(autorange="reversed"),
    margin=dict(l=120, r=40, t=30, b=40)
)

st.plotly_chart(fig_barras, use_container_width=True)

st.caption(
    """
    La población corresponde a estimaciones de la ENOE para el año seleccionado.
    El gráfico muestra concentración absoluta y no debe interpretarse como proporción
    respecto a la población total de cada entidad.
    """
)

# ==================================================
# SECCIÓN 5 — NOTA METODOLÓGICA
# ==================================================
st.header("Nota metodológica")

st.markdown(
    """
    **Periodo de referencia**  
    El análisis utiliza el tercer trimestre (julio–septiembre) de cada año como aproximación anual
    de las condiciones laborales. Este trimestre presenta menor volatilidad estacional
    y es el utilizado por INEGI para los comparativos interanuales y balances estructurales
    del mercado laboral.

    **Ingresos laborales**  
    Los ingresos provienen de la ENOE. Para el análisis en pesos constantes,
    los montos se deflactaron a precios de 2025 utilizando el Índice Nacional de Precios
    al Consumidor (INPC), conforme a la metodología de análisis de ingresos laborales
    desarrollada por Fundar.

    **Salario mínimo**  
    El salario mínimo legal se obtuvo de la Comisión Nacional de los Salarios Mínimos (CONASAMI).
    Para hacerlo comparable con los ingresos mensuales de la ENOE,
    el salario mínimo diario se convirtió a ingreso mensual multiplicándolo por 30.4,
    conforme al criterio estadístico utilizado por INEGI.

    **Alcances y limitaciones**  
    Los resultados son descriptivos y no permiten inferencia causal.
    Las estimaciones estatales deben interpretarse con cautela debido a tamaños poblacionales
    pequeños y variabilidad muestral.

    Persistencia territorial
    La persistencia territorial se definió a partir de la recurrencia de categorías de precariedad 
    laboral por entidad federativa a lo largo del periodo 2023–2025.
    Se consideró que una entidad presenta alta precariedad persistente cuando fue clasificada en la
    categoría de “Alta” en al menos dos de los tres años analizados. Esta definición permite identificar
    patrones estructurales sin depender de variaciones anuales puntuales.
    La persistencia territorial se define a partir de la recurrencia de categorías de precariedad laboral
    y no depende del tamaño poblacional del grupo en cada entidad.
    Para contextualizar su alcance, se incorpora la proporción de mujeres jornaleras dentro de la población
    jornalera de cada estado, lo que permite distinguir territorios donde la precariedad es estructuralmente
    central del modelo productivo agrícola de aquellos donde el fenómeno es más acotado en términos de 
    composición ocupacional.
    """
)