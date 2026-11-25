import numpy as np

def calcular_score_rubro(precio_lista_ref: float, precio_promo_ref: float, precio_medio: float) -> float:
    ratio_lista = precio_medio / precio_lista_ref
    score_lista = np.clip(ratio_lista * 35, 0, 50)
    
    ratio_final = precio_medio / precio_promo_ref
    score_final = np.clip(ratio_final * 25, 0, 35)
    
    tiene_promo = 15 if precio_promo_ref < precio_lista_ref else 0
    return round(float(score_lista + score_final + tiene_promo), 2)
