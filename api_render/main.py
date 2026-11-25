from fastapi import FastAPI

from esquemas import LoteScraping
from procesamiento import procesar_lote

app = FastAPI(title="API Inteligencia Competitiva - 10 Rubros Testigo")


@app.post("/procesar-lote")
def ruta_procesar_lote(lote: LoteScraping):
    return procesar_lote(lote)
