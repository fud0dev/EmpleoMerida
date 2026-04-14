# EmpleoMérida 💼

Un portal centralizado y automatizado que recopila las ofertas de empleo público y privado disponibles para la ciudad de Mérida (Badajoz), unificando distintas fuentes gubernamentales en un único *dashboard* limpio, rápido y fácil de usar.

Este proyecto forma parte del ecosistema de servicios locales [**Mérida XYZ**](https://meridaxyz.wordpress.com/).

## ⚙️ Arquitectura y Funcionamiento

El proyecto está diseñado bajo un modelo de **datos estáticos auto-actualizables (Serverless)** hospedado íntegramente de forma gratuita en GitHub Pages y GitHub Actions:

1. **Scraping**: Dos scripts desarrollados en Python (`fetch_sexpe.py` y `fetch_sne.py`) rastrean periódicamente los portales correspondientes. 
   - `fetch_sexpe.py` utiliza `Playwright` para lidiar con el renderizado dinámico del SEXPE.
   - `fetch_sne.py` utiliza la librería `httpx` para extraer la base de datos del Sistema Nacional de Empleo provincial y filtrar las oportunidades locales.
   
2. **Almacenamiento**: No se usan bases de datos tradicionales. En su lugar, los scripts exportan listas optimizadas directamente a la carpeta `/docs/data` en formato `.json` (p. ej., `sexpe.json`).

3. **Automatización (Cron Job)**: Mediante GitHub Actions (`.github/workflows/update_empleo.yml`), una máquina virtual en la nube ejecuta los scrapers todos los días a las **06:00 AM UTC**. Si detecta modificaciones u ofertas nuevas, el bot realiza un `git push` subiendo los nuevos archivos JSON.

4. **Frontend**: Los archivos situados en `/docs` sirven como un minisitio estático SPA (Single Page Application). Javascript en el cliente (`index.html`) lee los JSON estáticos y pinta las ofertas sin necesidad de un backend. 

## 🚀 Despliegue Local

Para ejecutar el código en tu propia máquina:

1. Clona el repositorio e instala las dependencias:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. Ejecuta los módulos de manera independiente para reescribir los archivos JSON:
   ```bash
   python fetch_sexpe.py
   python fetch_sne.py
   ```

3. Abre el archivo `docs/index.html` con cualquier navegador local. 

## ⚠️ Disclaimer – Aviso Legal y Educativo

**Este proyecto se ha desarrollado estricta y exclusivamente con fines divulgativos, experimentales y educativos.** 

* **No es un portal gubernamental oficial.** Ni el creador de este código ni el repositorio final tienen vínculo alguno con el Servicio Extremeño Público de Empleo (SEXPE), la Junta de Extremadura o el Sistema Nacional de Empleo de España.
* Toda la información mostrada es extraída de datos públicos ofrecidos de libre disposición de las mencionadas fuentes de origen. Los enlaces de "*Aplicar a la oferta*" redirigen irremediablemente a las sedes electrónicas e instalaciones oficiales correspondientes, donde el usuario debe someterse a las normas de privacidad del propio organismo público.
* El autor del repositorio declina cualquier responsabilidad por discrepancias de información, caídas en la ejecución algorítmica, finalización anticipada de plazas u otro evento resultante de una desincronización de los datos cacheados en este servicio frente a la base de datos original.
