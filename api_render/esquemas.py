from pydantic import BaseModel
from typing import List, Optional

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
