import pandas as pd
import numpy as np

from esquemas import LoteScraping
from modelo import modelo_detector, mapa_referencia
from rubros import clasificar_rubro
from scoring import calcular_score_rubro
from reporte import construir_reporte


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
