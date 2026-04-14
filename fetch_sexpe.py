"""
=============================================================================
 fetch_sexpe.py  –  Scraper SEXPE adaptado para Merida-Empleo Dashboard
=============================================================================
• Scrapea las ofertas usando Playwright.
• Exporta los resultados a docs/data/sexpe.json
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

URL      = "https://sexpeemplea.juntaex.es/OfertasOrientacion/?id_menu=462&ssid=RT3F12A35B"
BASE_URL = "https://sexpeemplea.juntaex.es"

TIMEOUT_ESPERA = 25_000   
PAUSA_EXTRA    = 2        

# Guardar los datos procesados en la carpeta /docs/data/ para GitHub Pages
DATA_FILE = Path(__file__).parent / "docs" / "data" / "sexpe.json"

# =============================================================================
# PLAYWRIGHT: cargar página y obtener HTML
# =============================================================================

def obtener_html_con_playwright() -> str | None:
    print(f"[INFO] Iniciando Playwright (Chromium headless)…")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()
        print(f"[INFO] Accediendo a: {URL}")
        try:
            page.goto(URL, timeout=TIMEOUT_ESPERA)
        except PlaywrightTimeout:
            print("[ERROR] Timeout al cargar la página.")
            browser.close()
            return None
        except Exception as e:
            print(f"[ERROR] No se pudo cargar la página: {e}")
            browser.close()
            return None

        # Esperar a que aparezca un <select> con al menos 2 opciones
        try:
            page.wait_for_selector("select option:nth-child(2)", timeout=TIMEOUT_ESPERA)
            print("[INFO] <select> con opciones detectado.")
        except PlaywrightTimeout:
            print("[AVISO] Timeout esperando el <select>. Se intentará parsear lo disponible.")

        time.sleep(PAUSA_EXTRA)
        html = page.content()
        browser.close()
        return html


# =============================================================================
# BEAUTIFULSOUP: extraer ofertas del <select>
# =============================================================================

def extraer_ofertas(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    ofertas = []
    select_oferta = None

    for label in soup.find_all("label"):
        texto_label = label.get_text(strip=True).upper()
        if "OFERTA DE EMPLEO" in texto_label or "OFERTA" in texto_label:
            select_id = label.get("for")
            if select_id:
                select_oferta = soup.find("select", id=select_id)
            if not select_oferta:
                select_oferta = label.find_next("select")
            if select_oferta:
                print(f"[INFO] <select> encontrado via label: '{texto_label[:40]}'")
                break

    if not select_oferta:
        todos = soup.find_all("select")
        candidatos = [s for s in todos if len(s.find_all("option")) > 2]
        if candidatos:
            select_oferta = max(candidatos, key=lambda s: len(s.find_all("option")))
            print(f"[INFO] <select> por cantidad de opciones ({len(select_oferta.find_all('option'))}).")

    if not select_oferta:
        print("[AVISO] No se encontró <select>. Usando extracción alternativa…")
        return _extraer_fallback(soup)

    for opcion in select_oferta.find_all("option"):
        titulo = opcion.get_text(strip=True)
        value  = opcion.get("value", "").strip()
        if not titulo or not value or value in ("0", ""):
            continue
        if "seleccione" in titulo.lower() or "elija" in titulo.lower():
            continue
        if value.isdigit():
            enlace = f"{BASE_URL}/OfertasOrientacion/?id_menu={value}"
        elif value.startswith("http"):
            enlace = value
        else:
            enlace = f"{BASE_URL}/OfertasOrientacion/{value}"
        
        # Formato unificado para el Dashboard
        ofertas.append({
            "titulo": titulo.capitalize() if titulo.isupper() else titulo,
            "id": value,
            "enlace": enlace,
            "fuente": "SEXPE",
            "ubicacion": "Mérida (Automático)"
        })

    return ofertas

def _extraer_fallback(soup: BeautifulSoup) -> list[dict]:
    ofertas = []
    palabras_clave = ["oferta", "empleo", "vacante", "puesto", "id_oferta", "id_empleo"]
    for a_tag in soup.find_all("a", href=True):
        href  = a_tag["href"]
        texto = a_tag.get_text(strip=True)
        if not texto or len(texto) < 5:
            continue
        if any(k in href.lower() for k in palabras_clave):
            enlace = href if href.startswith("http") else BASE_URL + "/" + href.lstrip("/")
            ofertas.append({
                "titulo": texto.capitalize() if texto.isupper() else texto,
                "id": "-",
                "enlace": enlace,
                "fuente": "SEXPE",
                "ubicacion": "Mérida (Automático)"
            })
    return ofertas


# =============================================================================
# EXPORTAR JSON (FRONTEND)
# =============================================================================

def guardar_json(ofertas: list) -> None:
    """Sobrescribe el archivo data/sexpe.json con los últimos datos y un timestamp."""
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

def main() -> None:
    print(f"[INFO] Inicio Scraper SEXPE: {datetime.now().isoformat()}")

    try:
        html = obtener_html_con_playwright()
    except Exception as e:
        print(f"[ERROR CRÍTICO] Playwright falló: {e}")
        sys.exit(1)

    if html is None:
        print("[ERROR] No se pudo obtener el HTML de la página SEXPE.")
        sys.exit(1)

    print("[INFO] Analizando contenido de la página…")
    todas = extraer_ofertas(html)
    print(f"[INFO] Total ofertas SEXPE: {len(todas)}")
    
    guardar_json(todas)
    
    print(f"[INFO] Fin: {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()
