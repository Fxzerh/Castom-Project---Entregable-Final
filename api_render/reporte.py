import csv
import io
import html

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
