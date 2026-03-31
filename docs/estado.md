# Estado del proyecto de scraping (TFG)

Fecha: 2026-03-30
Rama de trabajo: dev

## Actualización de esta iteración

- Notebook renombrado: `notebooks/pruebas_scraping_fuentes.ipynb`.
- Pipeline ETL implementado: `src/etl.py`.
- Automatización diaria en macOS (launchd) activa con:
- Automatización diaria en macOS preparada con launchd:
	- `scripts/run_daily_pipeline.sh`
	- `launchd/com.tfg.scraper.daily.plist`
- Automatización diaria efectiva activada con `crontab` (09:00):
	- `0 9 * * * /Users/david/Documents/scraper/scripts/run_daily_pipeline.sh`
- Ingesta alternativa para datasets externos (Plan E): `src/ingest_external_dataset.py`.
- Notebook de analisis temporal creado: `notebooks/analisis_temporal_tfg.ipynb`.


## Objetivo
Extraer precios de portátiles para análisis de dynamic pricing en e-commerce español.

## Hallazgos técnicos confirmados

1. PcComponentes con requests + BeautifulSoup
- Resultado: sin productos útiles.
- Causa: renderizado JS y protección anti-bot.

2. Playwright Sync API en Jupyter
- Resultado: error de loop asíncrono.
- Causa: incompatibilidad con el event loop de Jupyter.

3. Playwright Async API en PcComponentes
- Resultado: timeout o contenido no esperado.
- Causa probable: detección de automatización.

4. playwright-stealth
- Hallazgo: la API actual no usa `stealth_async`.
- Solución aplicada en notebook: `from playwright_stealth import Stealth` + `await Stealth().apply_stealth_async(context)`.

5. Plan D (Idealo) validado en este entorno
- Prueba HTTP real: `GET https://www.idealo.es/cat/3394/portatiles.html`.
- Resultado: `HTTP 503` (Akamai), HTML de error de ~4 KB.
- Conclusión: Plan D bloqueado desde esta red/huella de cliente.

6. Playwright + Stealth (estado actual)
- PcComponentes: acceso correcto con HTML completo (~1.19 MB) y detección de productos.
- Amazon.es: acceso correcto con detección de resultados de búsqueda.
- MediaMarkt.es: respuesta con marcadores de bloqueo; no estable en este entorno.
- Evidencia de extracción: `data/raw/precios_portatiles_20260330_1250.csv` con 25 productos de Amazon y 25 de PcComponentes.

## Estado por plataforma objetivo

- Amazon.es: viable con Playwright + Stealth (scraping funcional).
- MediaMarkt.es: no viable por ahora (bloqueo anti-bot persistente).
- PcComponentes.com: viable con Playwright + Stealth (scraping funcional).

## Resultado práctico conseguido

Actualmente el proyecto ya obtiene de forma automatizada y repetible:

- Nombre del producto.
- Precio actual.
- Precio original (cuando existe).
- Valoración textual (cuando existe, especialmente en Amazon).
- Plataforma.
- Fecha y hora de extracción.

Además, el ETL calcula:

- Precio actual numérico (`precio_actual_num`).
- Precio original numérico (`precio_original_num`).
- Descuento porcentual (`descuento_pct`) cuando aplica.

## Estrategia recomendada (viable para TFG)

Estrategia híbrida de datos:

1. Fuente principal robusta: feeds/APIs de afiliación o datasets públicos con cobertura de e-commerce.
2. Fuente secundaria de validación: scraping puntual controlado (baja frecuencia) para contraste metodológico.
3. Registro diario automatizado: guardar snapshots con timestamp en `data/raw/`.

## Criterios mínimos para seguir

- Mínimo: `nombre`, `precio_actual`, `fecha`.
- Ideal: `precio_original`, `descuento`, `valoración`.

## Próximos pasos inmediatos

1. Mantener scraping diario con `src/scraper.py` para Amazon + PcComponentes.
2. Configurar ejecución diaria (cron o launchd en macOS).
3. Añadir control de calidad de datos (duplicados, nulos, normalización de precio).
4. Evaluar fuente alternativa para sustituir MediaMarkt (feed afiliación o dataset público).

## Explicación de alto nivel (arquitectura)

Flujo completo actual:

1. `src/scraper.py` entra a Amazon y PcComponentes con Playwright + Stealth.
2. Guarda extracción cruda con timestamp en `data/raw/precios_portatiles_YYYYMMDD_HHMM.csv`.
3. `src/etl.py` toma el último CSV de `raw`, limpia y normaliza.
4. Guarda resultado analítico en `data/processed/precios_portatiles_procesado_YYYYMMDD_HHMM.csv`.
5. launchd ejecuta diariamente ambos pasos mediante `scripts/run_daily_pipeline.sh`.

## Explicación de la carpeta data

### `data/raw`

Es la capa de evidencia y trazabilidad. Aquí va lo que “sale de la web” casi sin tocar.

- CSV crudos del scraping.
- HTML de diagnóstico y verificación de bloqueos.
- Logs de ejecución automática (`pipeline.log`, `launchd_stdout.log`, `launchd_stderr.log`).

Uso principal: auditoría metodológica del TFG y reproducibilidad.

### `data/processed`

Es la capa lista para análisis estadístico y dashboard.

- Precios en formato numérico.
- Descuento calculado.
- Fechas parseadas.
- Deduplicación básica.

Uso principal: análisis temporal, visualizaciones y conclusiones.

## CSV generados: qué hacer e interpretación

Se han generado CSV crudos válidos (por ejemplo `precios_portatiles_20260330_1250.csv`).

Qué hacer con ellos:

1. No los borres: son la evidencia de extracción diaria.
2. Procesa cada uno con `src/etl.py` (ya automatizado).
3. Analiza sobre `data/processed`, no sobre `raw`.

Cómo interpretarlos:

- Cada fila = producto capturado en un instante de tiempo.
- Si un mismo producto aparece con precios distintos en días distintos, eso es señal de dynamic pricing.
- Si `precio_original` existe y es mayor que `precio_actual`, hay promoción/descuento activo.

## HTML guardados: para qué sirven

Sí, se pueden abrir en local con navegador (doble clic o arrastrar al navegador):

- `data/raw/pagina.html`: evidencia de challenge/bloqueo (Cloudflare).
- `data/raw/pagina_pccomponentes.html`: HTML completo capturado en sesión funcional.

No son para análisis final de precios, sino para:

- Diagnosticar por qué falla o funciona un scraper.
- Documentar robustez técnica en la memoria del TFG.

## Sobre el notebook de pruebas

El notebook se renombró a `notebooks/pruebas_scraping_fuentes.ipynb` porque ya no prueba solo PcComponentes; ahora cubre diagnóstico de varias fuentes y ejecución del pipeline.

Contenido útil logrado en notebook:

- Diagnóstico de anti-bot (Idealo y PcComponentes).
- Verificación de API actual de `playwright-stealth`.
- Ejecución de scraping diario en modo notebook y visualización del DataFrame resultante.

## Automatización diaria (estado)

Automatización configurada de dos formas:

- Label: `com.tfg.scraper.daily`
- Hora programada: 09:00
- Ejecución inmediata al cargar: sí (`RunAtLoad`)
- Script ejecutado: `scripts/run_daily_pipeline.sh`

Nota operativa importante en macOS:

- En esta máquina, launchd en background muestra restricción de acceso a rutas bajo `Documents` (TCC/privacy), por lo que la ejecución fiable diaria se deja activa por `crontab`.
- Launchd queda como configuración preparada/documentada para reutilizar si se mueve el proyecto fuera de `Documents` o se ajustan permisos del sistema.

## Fuente alternativa (Plan E) ya preparada

Si MediaMarkt sigue bloqueado, el módulo `src/ingest_external_dataset.py` permite incorporar un CSV externo (Kaggle u otra fuente pública) al mismo esquema de columnas para mantener continuidad histórica y consistencia metodológica.

## Estado del analisis temporal

Notebook activo: `notebooks/analisis_temporal_tfg.ipynb`.

Resultados actuales con el ultimo dataset procesado:

- Observaciones analizadas: 49
- Plataformas detectadas: Amazon y PcComponentes
- Precio medio Amazon: 431.08 EUR
- Precio medio PcComponentes: 957.28 EUR

Interpretacion:

- El pipeline analitico ya funciona de extremo a extremo.
- Como aun hay pocos dias acumulados, la variacion temporal inter-diaria es limitada y se espera que aumente al consolidar historico diario.
