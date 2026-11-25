from pathlib import Path
import joblib
import pandas as pd

# 1. Cargamos el modelo y la tabla de precios medios de referencia al iniciar
BASE_DIR = Path(__file__).resolve().parent  # carpeta de este archivo (api_render/)

def cargar_modelo():
    """Carga el modelo ya entrenado desde su archivo, sin depender del directorio de trabajo."""
    return joblib.load(BASE_DIR / "detector_anomalias_v2.joblib")

modelo_detector = cargar_modelo()
df_ref = pd.read_csv(BASE_DIR / "canasta_representativa_10_rubros_v2.csv")
mapa_referencia = dict(zip(df_ref['tipo_producto'], df_ref['precio_mercado_medio']))
