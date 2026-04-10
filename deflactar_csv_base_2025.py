import pandas as pd
import sys
from pathlib import Path

# ----------------------------------
# Parámetros editables
# ----------------------------------
_ROOT = Path(__file__).parent

# Si se pasa como argumento: python deflactar_csv_base_2025.py mi_tabla.csv
# Si no, se usa el valor por defecto definido aquí:
ARCHIVO_DATOS = Path(sys.argv[1]) if len(sys.argv) > 1 else _ROOT / "Datos" / "ENOE" / "tabla_nacional_jornaleria_agricola_2023a2025_final.csv"
ARCHIVO_DEFLACTORES = _ROOT / "Datos" / "Deflactor" / "deflactores.csv"
ANIO_BASE = 2025

# ----------------------------------
# 1. Cargar datos
# ----------------------------------
df = pd.read_csv(ARCHIVO_DATOS)

if "anio" not in df.columns:
    raise ValueError("El archivo debe contener una columna llamada 'anio'")

# ----------------------------------
# 2. Preparar deflactores
# ----------------------------------
deflactores_raw = pd.read_csv(ARCHIVO_DEFLACTORES)

# Normalizar nombres: primera columna = anio, segunda = indice
deflactores_raw.columns = deflactores_raw.columns.str.strip()
deflactores_raw = deflactores_raw.rename(columns={
    deflactores_raw.columns[0]: "anio",
    deflactores_raw.columns[1]: "indice"
})

# Obtener índice del año base
indice_base = deflactores_raw.loc[deflactores_raw["anio"] == ANIO_BASE, "indice"]
if indice_base.empty:
    raise ValueError(f"El archivo de deflactores no contiene el año base {ANIO_BASE}")
indice_base = indice_base.iloc[0]

# Factor de deflactación: índice_base / índice_año
deflactores_raw["factor_deflactor"] = indice_base / deflactores_raw["indice"]

# ----------------------------------
# 3. Unir deflactores
# ----------------------------------
df = df.merge(deflactores_raw[["anio", "factor_deflactor"]], on="anio", how="left")

if df["factor_deflactor"].isna().any():
    anios_faltantes = df.loc[df["factor_deflactor"].isna(), "anio"].unique()
    raise ValueError(f"Faltan deflactores para los años: {anios_faltantes}")

# ----------------------------------
# 3. Detectar columnas monetarias
# ----------------------------------
def es_columna_ingreso(col):
    col_l = col.lower()
    return (
        "ingreso" in col_l
        and not any(x in col_l for x in [
            "horas",
            "prop",
            "indice",
            "poblacion",
            "porcentaje",
            "categoria",
            "cv",
            "confiable"
        ])
    )

columnas_ingreso = [c for c in df.columns if es_columna_ingreso(c)]

if not columnas_ingreso:
    print("⚠️ No se detectaron columnas de ingreso. El archivo se guardará sin cambios.")
else:
    print("Columnas de ingreso detectadas:")
    for c in columnas_ingreso:
        print(f"  - {c}")

# ----------------------------------
# 4. Deflactar
# ----------------------------------
for col in columnas_ingreso:
    nueva_col = f"{col}_real_{ANIO_BASE}"
    df[nueva_col] = df[col] * df["factor_deflactor"]

df = df.drop(columns=["factor_deflactor"])

# ----------------------------------
# 5. Guardar resultado
# ----------------------------------
ruta = Path(ARCHIVO_DATOS)
salida = ruta.with_name(f"{ruta.stem}_precios_constantes_{ANIO_BASE}.csv")

df.to_csv(salida, index=False)

print(f"\n✅ Archivo generado: {salida.name}")
