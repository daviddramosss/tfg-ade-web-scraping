PROMPT PARA CLAUDE - ACTUALIZACION DEL ESTADO DEL TFG

Actua como asistente experto en Python, web scraping, analisis de datos y metodologia de TFG en ADE.
Necesito que uses este contexto para continuar mi proyecto de forma consistente, sin romper lo ya implementado.

CONTEXTO GENERAL DEL TFG
- Titulo: Big Data e Inteligencia Competitiva en el E-commerce: Analisis de estrategias de precios dinamicos en electronica de consumo mediante web scraping.
- Objetivo academico: construir una base historica de precios de portatiles para detectar patrones de dynamic pricing.
- Entorno: macOS, Python 3.12.8, VS Code, Jupyter, venv.
- Librerias clave: requests, beautifulsoup4, pandas, plotly, dash, playwright, playwright-stealth.

OBJETIVO DEL PROYECTO (POR QUE HACEMOS TODO ESTO)
- Capturar precios de forma recurrente en e-commerce.
- Almacenar historico temporal con evidencia reproducible.
- Limpiar y estandarizar datos para analisis riguroso.
- Extraer hallazgos de variacion de precios para responder preguntas de investigacion del TFG.

ESTADO TECNICO REAL A DIA DE HOY
1) Fuentes y viabilidad
- PcComponentes: viable con Playwright async + Stealth.
- Amazon.es: viable con Playwright async + Stealth.
- MediaMarkt.es: no viable por ahora por bloqueo anti-bot.
- Idealo (Plan D): bloqueado en este entorno (Akamai/503 o cierre de conexion).

2) Scraping implementado
- Modulo operativo: src/scraper.py
- Funcion principal: run_daily_scrape(max_items_per_platform, headless)
- Output: CSV crudo en data/raw con timestamp (precios_portatiles_YYYYMMDD_HHMM.csv)
- Columnas base: nombre, precio_actual, precio_original, descuento, valoracion, plataforma, fecha

3) ETL implementado
- Modulo: src/etl.py
- Entrada: ultimo CSV de data/raw
- Salida: CSV procesado en data/processed (precios_portatiles_procesado_YYYYMMDD_HHMM.csv)
- Transformaciones:
  - Parseo de precio a numerico (precio_actual_num, precio_original_num)
  - Calculo descuento_pct cuando procede
  - Parseo de fecha_extraccion
  - Deduplicacion basica
  - Variables temporales anio, mes, dia

4) Analisis implementado
- Notebook de analisis: notebooks/analisis_temporal_tfg.ipynb
- Incluye:
  - Evolucion diaria de precio medio por plataforma
  - Ranking de productos con mayor variacion
  - Resumen ejecutivo automatico
- Estado actual: funciona y detecta que aun falta mas historial para variaciones temporales robustas (normal, solo hay pocos dias)

5) Notebook de pruebas y diagnostico
- Renombrado a: notebooks/pruebas_scraping_fuentes.ipynb
- Contiene pruebas de:
  - stealth con playwright-stealth API actual
  - diagnostico anti-bot
  - test Idealo
  - ejecucion de scraping diario desde notebook

6) Automatizacion
- Script diario: scripts/run_daily_pipeline.sh
  - Ejecuta scraping y luego ETL
- Launchd preparado: launchd/com.tfg.scraper.daily.plist
  - En esta maquina tiene limitacion por permisos de macOS sobre Documents en background
- Automatizacion efectiva activa: crontab
  - 0 9 * * * /Users/david/Documents/scraper/scripts/run_daily_pipeline.sh

7) Documentacion viva
- Archivo principal de estado: docs/estado.md
- Incluye arquitectura, hallazgos, interpretacion de datos, explicacion de data/raw y data/processed y estado de automatizacion.

ESTRUCTURA FUNCIONAL ACTUAL
- src/scraper.py
- src/etl.py
- src/ingest_external_dataset.py  (Plan E para integrar datasets externos)
- notebooks/pruebas_scraping_fuentes.ipynb
- notebooks/analisis_temporal_tfg.ipynb
- scripts/run_daily_pipeline.sh
- launchd/com.tfg.scraper.daily.plist
- docs/estado.md

QUE NECESITO QUE HAGAS A PARTIR DE AQUI
1) Revisar todo este estado y proponer una hoja de ruta de 2 a 4 semanas para cerrar el TFG.
2) Definir KPIs concretos para dynamic pricing (variacion diaria, dispersion, frecuencia de cambio, intensidad promo, etc.).
3) Proponer limpieza y matching de productos entre dias/plataformas para mejorar comparabilidad.
4) Proponer una metodologia academica defendible (limitaciones, sesgos, validez, reproducibilidad).
5) Sugerir estructura de capitulos para memoria y como vincular resultados empiricos con marco teorico.
6) Proponer el siguiente bloque de codigo prioritario para mejorar el proyecto (sin romper lo existente).

RESTRICCIONES
- No romper modulos existentes.
- Mantener compatibilidad con macOS + Python 3.12.8 + Jupyter.
- Priorizar robustez y trazabilidad academica.
- Mantener enfoque etico y legal del scraping.

ENTREGABLE DE RESPUESTA QUE ESPERO
- Resumen ejecutivo breve.
- Plan accionable por fases.
- Mejoras tecnicas concretas (codigo/arquitectura).
- Riesgos y mitigaciones.
- Checklist de validacion para el TFG.
