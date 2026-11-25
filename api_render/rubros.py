from typing import Optional
import unicodedata

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
