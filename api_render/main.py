from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import unicodedata
import csv
import io
import html
import joblib
import pandas as pd
import numpy as np

app = FastAPI(title="API Inteligencia Competitiva - 10 Rubros Testigo")

# 1. Cargamos el modelo y la tabla de precios medios de referencia al iniciar
modelo_detector = joblib.load("detector_anomalias_v2.joblib")
df_ref = pd.read_csv("canasta_representativa_10_rubros_v2.csv")
mapa_referencia = dict(zip(df_ref['tipo_producto'], df_ref['precio_mercado_medio']))

# Palabras clave exactas usadas en Colab para clasificar los 10 rubros
TIPOS_PRODUCTOS = {
    'Leche': ['LECHE ENTERA', 'LECHE UAT', 'LECHE DESCREMADA'],
    'Yerba': ['YERBA MATE'],
    'Aceite': ['ACEITE GIRASOL', 'ACEITE DE GIRASOL'],
    'Fideos': ['FIDEOS'],
    'Arroz': ['ARROZ LARGO', 'ARROZ PARBOIL'],
    'Azucar': ['AZUCAR'],
    'Queso': ['QUESO CREMOSO', 'QUESO RALLADO'],
    'Gaseosa': ['GASEOSA COLA', 'COCA COLA', 'PEPSI'],
    'Detergente': ['DETERGENTE'],
    'Papel Higienico': ['PAPEL HIGIENICO']
}

def normalizar(texto: str) -> str:
    texto = str(texto).upper()
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )

def clasificar_rubro(descripcion: str) -> Optional[str]:
    desc = normalizar(descripcion)
    for rubro, palabras in TIPOS_PRODUCTOS.items():
        if any(normalizar(p) in desc for p in palabras):
            return rubro
    return None

# Estructura de cada ítem crudo que Apify extrae y Make reenvía
class ProductoScrapeado(BaseModel):
    supermercado: str
    id_producto: str
    descripcion: str
    precio_lista: float
    precio_referencia: float  # Precio por kg/litro extraído de la web
    precio_promo: Optional[float] = None

class LoteScraping(BaseModel):
    fecha: str
    productos: List[ProductoScrapeado]

def calcular_score_rubro(precio_lista_ref: float, precio_promo_ref: float, precio_medio: float) -> float:
    ratio_lista = precio_medio / precio_lista_ref
    score_lista = np.clip(ratio_lista * 35, 0, 50)
    
    ratio_final = precio_medio / precio_promo_ref
    score_final = np.clip(ratio_final * 25, 0, 35)
    
    tiene_promo = 15 if precio_promo_ref < precio_lista_ref else 0
    return round(float(score_lista + score_final + tiene_promo), 2)

def _ar(n: float) -> str:
    """Formato argentino: 2219.5 -> 2.219,50"""
    return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def _fila_validado(r: dict) -> str:
    score = r["score_competitividad"]
    n = max(1, min(5, int(score / 20 + 0.5)))
    if score >= 70:
        semaforo = "🟢"
    elif score >= 50:
        semaforo = "🟡"
    else:
        semaforo = "🔴"
    promo_style = " color: #15803d; font-weight: bold;" if r["precio_promo_ref"] < r["precio_lista_ref"] else ""
    return f"""<tr style="border-bottom: 1px solid #e2e8f0;">
  <td style="padding: 10px;"><strong>{html.escape(r['supermercado'])}</strong></td>
  <td style="padding: 10px;">{html.escape(r['tipo_producto'])}</td>
  <td style="padding: 10px; text-align: right;">${_ar(r['precio_lista_ref'])}</td>
  <td style="padding: 10px; text-align: right;{promo_style}">${_ar(r['precio_promo_ref'])}</td>
  <td style="padding: 10px; text-align: center;">{score:.1f}</td>
  <td style="padding: 10px; text-align: center; color: #f59e0b; font-size: 16px; letter-spacing: 1px; white-space: nowrap;">{'★' * n}<span style="color: #cbd5e1;">{'☆' * (5 - n)}</span></td>
  <td style="padding: 10px; text-align: center; white-space: nowrap;">{semaforo}</td>
</tr>"""

def _fila_anomalia(r: dict) -> str:
    return f"""<tr style="border-bottom: 1px solid #e2e8f0;">
  <td style="padding: 10px;"><strong>{html.escape(r['supermercado'])}</strong></td>
  <td style="padding: 10px;">{html.escape(r['tipo_producto'])}</td>
  <td style="padding: 10px; text-align: right;">${_ar(r['precio_lista_ref'])}</td>
  <td style="padding: 10px; text-align: right;">${_ar(r['precio_promo_ref'])}</td>
  <td style="padding: 10px; text-align: right;">${_ar(r['precio_mercado_medio'])}</td>
  <td style="padding: 10px; color: #b91c1c;">⚠️ {html.escape(r['motivo'])}</td>
</tr>"""

def construir_reporte(validados: list, anomalias: list) -> dict:
    campos = ["estado", "fecha", "supermercado", "tipo_producto", "precio_lista_ref",
              "precio_promo_ref", "precio_mercado_medio", "cantidad_opciones",
              "score_competitividad", "motivo"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=campos, extrasaction="ignore", restval="")
    writer.writeheader()
    for r in validados:
        writer.writerow({**r, "estado": "validado"})
    for r in anomalias:
        writer.writerow({**r, "estado": "anomalia"})

    return {
        "html_validados": "\n".join(_fila_validado(r) for r in validados),
        "html_anomalias": "\n".join(_fila_anomalia(r) for r in anomalias),
        "csv": "\ufeff" + buf.getvalue(),  # BOM para que Excel respete las tildes
    }

@app.post("/procesar-lote")
def procesar_lote(lote: LoteScraping):
    # Convertimos el JSON recibido a DataFrame
    df = pd.DataFrame([p.model_dump() for p in lote.productos])
    if df.empty:
        return {"mensaje": "Lote vacío", "validados": [], "anomalias": []}

    # Limpieza básica y clasificación en los 10 rubros
    df = df[(df['precio_lista'] > 0) & (df['precio_referencia'] > 0)].copy()
    df['tipo_producto'] = df['descripcion'].apply(clasificar_rubro)
    df = df.dropna(subset=['tipo_producto'])

    # Normalizamos promo por kilo/litro
    df['precio_promo_limpio'] = np.where(
        (df['precio_promo'].notnull()) & (df['precio_promo'] > 0) & (df['precio_promo'] <= df['precio_lista']),
        df['precio_promo'],
        df['precio_lista']
    )
    df['ratio_ref'] = df['precio_referencia'] / df['precio_lista']
    df['precio_promo_ref'] = df['precio_promo_limpio'] * df['ratio_ref']

    # Agrupamos por supermercado y rubro (balanceando a 10 filas por súper)
    agrupado = (
        df.groupby(['supermercado', 'tipo_producto'], as_index=False)
        .agg(
            precio_lista_ref=('precio_referencia', 'median'),
            precio_promo_ref=('precio_promo_ref', 'median'),
            cantidad_opciones=('id_producto', 'nunique')
        )
    )

    validados = []
    anomalias = []

    for _, row in agrupado.iterrows():
        rubro = row['tipo_producto']
        precio_medio = mapa_referencia.get(rubro, row['precio_lista_ref'])

        ratio_vs_mercado = row['precio_lista_ref'] / precio_medio
        descuento_anunciado = (row['precio_lista_ref'] - row['precio_promo_ref']) / row['precio_lista_ref']
        ratio_promo_vs_mercado = row['precio_promo_ref'] / precio_medio

        df_eval = pd.DataFrame([{
            'ratio_vs_mercado': ratio_vs_mercado,
            'descuento_anunciado': descuento_anunciado,
            'ratio_promo_vs_mercado': ratio_promo_vs_mercado
        }])

        es_normal = modelo_detector.predict(df_eval)[0] == 1

        registro = {
            "fecha": lote.fecha,
            "supermercado": row['supermercado'],
            "tipo_producto": rubro,
            "precio_lista_ref": round(float(row['precio_lista_ref']), 2),
            "precio_promo_ref": round(float(row['precio_promo_ref']), 2),
            "precio_mercado_medio": round(float(precio_medio), 2),
            "cantidad_opciones": int(row['cantidad_opciones'])
        }

        if es_normal:
            registro["score_competitividad"] = calcular_score_rubro(
                row['precio_lista_ref'], row['precio_promo_ref'], precio_medio
            )
            validados.append(registro)
        else:
            registro["motivo"] = "Precio atípico en el rubro detectado por IA"
            anomalias.append(registro)

    respuesta = {
        "total_rubros_evaluados": len(agrupado),
        "cantidad_validados": len(validados),
        "cantidad_anomalias": len(anomalias),
        "validados": validados,
        "anomalias": anomalias
    }
    respuesta.update(construir_reporte(validados, anomalias))
    return respuesta
