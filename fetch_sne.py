"""
=============================================================================
 fetch_sne.py  –  Scraper SNE adaptado para Merida-Empleo Dashboard
=============================================================================
• Scrapea las ofertas de Mérida del Sistema Nacional de Empleo usando HTTPX.
• Exporta los resultados a docs/data/sne.json
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from html.parser import HTMLParser

import httpx

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

BASE         = "https://www.sistemanacionalempleo.es/OfertaDifusionWEB"
URL_BUSQUEDA = f"{BASE}/busquedaOfertas.do?modo=continuar&provincia=06&botonNavegacion=Enviar"
URL_PAGINA   = f"{BASE}/listadoOfertas.do"
URL_BASE_SNE = "https://www.sistemanacionalempleo.es"

DATA_FILE = Path(__file__).parent / "docs" / "data" / "sne.json"


# =============================================================================
# PARSER HTML SNE
# =============================================================================

class OfertasParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ofertas = []
        self._en_tabla = False
        self._fila_actual = []
        self._celda_texto = ""
        self._celda_href  = None
        self._en_td = False
        self._en_a  = False
        self._id_flujo = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr":
            self._fila_actual = []
        elif tag == "td":
            self._en_td = True
            self._celda_texto = ""
            self._celda_href  = None
        elif tag == "a" and self._en_td:
            href = attrs.get("href", "")
            if "detalleOferta" in href or "listadoOfertas" in href:
                self._celda_href = href
            self._en_a = True

    def handle_endtag(self, tag):
        if tag == "td" and self._en_td:
            self._fila_actual.append({
                "texto": self._celda_texto.strip(),
                "href":  self._celda_href,
            })
            self._en_td = False
            self._en_a  = False
        elif tag == "tr" and len(self._fila_actual) >= 3:
            enlace_celda = next(
                (c for c in self._fila_actual if c["href"] and "detalleOferta" in c["href"]),
                None
            )
            if enlace_celda:
                fecha     = self._fila_actual[0]["texto"]
                titulo    = enlace_celda["texto"]
                href      = enlace_celda["href"]
                ubicacion = self._fila_actual[-1]["texto"]

                id_match = re.search(r"id=([^&]+)", href)
                if id_match and re.match(r"\d{2}/\d{2}/\d{4}", fecha):
                     # Formato unificado para el Dashboard
                    self.ofertas.append({
                        "id": id_match.group(1),
                        "titulo": titulo.capitalize() if titulo.isupper() else titulo,
                        "fecha": fecha,
                        "ubicacion": ubicacion,
                        "enlace": URL_BASE_SNE + href if href.startswith("/") else href,
                        "fuente": "SNE"
                    })
            self._fila_actual = []

    def handle_data(self, data):
        if self._en_td:
            self._celda_texto += data


# =============================================================================
# SCRAPING HTTP
# =============================================================================

def obtener_ofertas_merida() -> list[dict]:
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
    }

    transport = httpx.HTTPTransport(retries=3)
    try:
        with httpx.Client(headers=headers, follow_redirects=True, timeout=60, transport=transport) as client:
            print("[INFO] Accediendo a resultados de Badajoz en SNE...")
            resp = client.get(URL_BUSQUEDA)
            resp.raise_for_status()
            html = resp.content.decode("iso-8859-1")

            id_flujo = re.search(r"idFlujo=([A-Za-z0-9_\-]+)", html)
            if not id_flujo:
                raise RuntimeError("No se pudo extraer idFlujo de la respuesta SNE")
            id_flujo = id_flujo.group(1)

            todas_ofertas = []

            def parsear_pagina(contenido_html: str):
                p = OfertasParser()
                p.feed(contenido_html)
                return p.ofertas

            ofertas_pag = parsear_pagina(html)
            todas_ofertas.extend(ofertas_pag)
            print(f"[INFO] Página 1: {len(ofertas_pag)} ofertas")

            indices = re.findall(
                r'listadoOfertas\.do\?modo=pagina&idFlujo=[^&]+&indice=(\d+)',
                html
            )
            indices = sorted(set(int(i) for i in indices if int(i) > 1), key=int)

            for indice in indices:
                url_pag = f"{URL_PAGINA}?modo=pagina&idFlujo={id_flujo}&indice={indice}"
                resp2 = client.get(url_pag)
                resp2.raise_for_status()
                html2 = resp2.content.decode("iso-8859-1")
                ofertas_pag = parsear_pagina(html2)
                todas_ofertas.extend(ofertas_pag)
                print(f"[INFO] Página (indice={indice}): {len(ofertas_pag)} ofertas")

        print(f"[INFO] Total ofertas provincia Badajoz SNE: {len(todas_ofertas)}")

        # Filtrar solo Mérida
        merida = [o for o in todas_ofertas if "merida" in o["ubicacion"].lower() or "mérida" in o["ubicacion"].lower()]
        print(f"[INFO] Total ofertas MÉRIDA SNE: {len(merida)}")
        return merida
        
    except Exception as e:
        print(f"[ERROR] Falló la petición a SNE: {e}")
        return []

# =============================================================================
# EXPORTAR JSON (FRONTEND)
# =============================================================================

def guardar_json(ofertas: list) -> None:
    os.makedirs(DATA_FILE.parent, exist_ok=True)
    
    fecha_hoy = datetime.now().strftime("%d/%m/%Y %H:%M")
    datos = {
        "last_updated": fecha_hoy,
        "count": len(ofertas),
        "ofertas": ofertas
    }
    
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
        
    print(f"[INFO] Guardado exitosamente archivo: {DATA_FILE}")

# =============================================================================
# MAIN
# =============================================================================

def main():
    print(f"[INFO] Inicio Scraper SNE: {datetime.now().isoformat()}")
    
    ofertas_merida = obtener_ofertas_merida()
    guardar_json(ofertas_merida)
    
    print(f"[INFO] Fin: {datetime.now().isoformat()}")

if __name__ == "__main__":
    main()
