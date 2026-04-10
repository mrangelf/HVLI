import pandas as pd
from pathlib import Path
import re
import warnings

# ==========================
# CONFIGURACIÓN
# ==========================

BASE_PATH = Path(__file__).parent / "Datos" / "ENOE" / "Anuales"

OUTPUT_PATH = Path(__file__).parent / "Datos" / "ENOE"


# ==========================
# FUNCIONES AUXILIARES
# ==========================

def parse_nombre_archivo(stem):
    """
    Extrae tipo de tabla, año y trimestre desde el nombre del archivo.
    Ejemplo esperado:
    tabla_composicion_agro_sexo_jornaleria_2023t3
    """
    pattern = r"(.*)_(\d{4})t(\d)$"
    match = re.search(pattern, stem)
    if not match:
        return None

    tipo = match.group(1)
    anio = int(match.group(2))
    trimestre = int(match.group(3))

    return tipo, anio, trimestre


def cargar_y_homogenizar(archivo, tipo, anio, trimestre):
    """
    Lee el CSV y agrega columnas de tiempo.
    NO modifica ni elimina columnas originales.
    """
    df = pd.read_csv(archivo, encoding="utf-8-sig")

    df = df.copy()
    df["anio"] = anio
    df["trimestre"] = trimestre

    return df


# ==========================
# PROCESO PRINCIPAL
# ==========================

def procesar_tablas(base_path):
    archivos = list(base_path.glob("*.csv"))
    # Excluir archivos que ya son salidas concatenadas de este script
    archivos = [a for a in archivos if not a.stem.endswith("_final")]
    tablas_por_tipo = {}

    for archivo in archivos:
        parsed = parse_nombre_archivo(archivo.stem)
        if parsed is None:
            print(f"Archivo ignorado (nombre no reconocido): {archivo.name}")
            continue

        tipo, anio, trimestre = parsed
        print(f"Procesando: {archivo.name}")

        df = cargar_y_homogenizar(archivo, tipo, anio, trimestre)
        tablas_por_tipo.setdefault(tipo, []).append(df)

    return tablas_por_tipo


# ==========================
# EJECUCIÓN
# ==========================

tablas = procesar_tablas(BASE_PATH)

for tipo, dfs in tablas.items():
    df_final = pd.concat(dfs, ignore_index=True)

    salida = OUTPUT_PATH / f"{tipo}_2023a2025_final.csv"
    df_final.to_csv(salida, index=False, encoding="utf-8-sig")

    print(f"Tabla final generada: {salida}")