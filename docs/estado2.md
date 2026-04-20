Informe de Estado — TFG Web Scraping de Precios
Fecha de análisis: 2026-04-19 | Rama activa: dev

1. Estructura del Proyecto

scraper/
├── src/
│   ├── scraper.py                  # Scraping principal (Playwright)
│   ├── etl.py                      # Pipeline de transformación
│   └── ingest_external_dataset.py  # Ingesta de datasets externos (Plan B)
├── notebooks/
│   ├── pruebas_scraping_fuentes.ipynb   # Tests y diagnósticos
│   └── analisis_temporal_tfg.ipynb      # Análisis de precios
├── data/
│   ├── raw/         # CSVs brutos + logs + HTML de diagnóstico
│   └── processed/   # CSVs limpios y normalizados
├── scripts/
│   └── run_daily_pipeline.sh       # Script de ejecución diaria
├── launchd/
│   └── com.tfg.scraper.daily.plist # Scheduler macOS (preparado)
└── docs/
    ├── estado.md                   # Documento de estado anterior
    └── prompt_actualizacion_claude.md
2. Objetivo del Código
El proyecto construye una base de datos histórica de precios de portátiles para analizar dynamic pricing en e-commerce. Los objetivos iniciales eran 4 fuentes, actualmente operativas 2:

Plataforma	Estado	Motivo
PcComponentes.com	✅ Operativa	Playwright + Stealth funciona
Amazon.es	✅ Operativa	Playwright + Stealth funciona
MediaMarkt.es	❌ Bloqueada	Anti-bot persistente
Idealo.es	❌ Bloqueada	Akamai HTTP 503
Datos que extrae por producto: nombre, precio_actual, precio_original, descuento, valoracion, plataforma, fecha

3. Stack Tecnológico
Componente	Tecnología
Scraping	playwright (async) + playwright-stealth
Procesado	pandas
Visualización	plotly (en notebooks)
Automatización	crontab + shell script (activo)
Scheduler alternativo	launchd (configurado pero restringido por macOS TCC)
Dashboard	dash — mencionado en README pero NO implementado
Base de datos	sqlite — planificado como database.py pero NO existe aún
4. Estado Actual y Flujo de Ejecución
Si ejecutas el pipeline ahora (./scripts/run_daily_pipeline.sh), ocurre lo siguiente:


1. [scraper.py]
   ├── Lanza Playwright en modo headless con Stealth
   ├── Navega a PcComponentes → extrae ~25 productos
   ├── Navega a Amazon.es → extrae ~24 productos
   └── Guarda: data/raw/precios_portatiles_YYYYMMDD_HHMM.csv

2. [etl.py]
   ├── Lee el CSV raw más reciente
   ├── Normaliza precios (€1.299,99 → float 1299.99)
   ├── Calcula descuento_pct real
   ├── Parsea fechas y extrae año/mes/día
   ├── Deduplica por (nombre, plataforma, fecha_extraccion)
   └── Guarda: data/processed/precios_portatiles_procesado_YYYYMMDD_HHMM.csv

3. [crontab] — se ejecuta automáticamente cada día a las 09:00
El último log exitoso fue el 30-03-2026 a las 13:02-13:03, con 49 productos capturados correctamente.

5. Datos de Salida
Archivos raw (data/raw/):

CSV con 7 columnas: nombre, precio_actual, precio_original, descuento, valoracion, plataforma, fecha
Actualmente: 3-4 archivos del 30-03-2026 (~49 registros cada uno, mismo día)
Archivos procesados (data/processed/):

CSV extendido que añade: precio_actual_num, precio_original_num, descuento_pct, fecha_extraccion, anio, mes, dia
Ordenado por fecha_extraccion DESC, plataforma ASC, precio_actual_num ASC
Muestra real de datos extraídos:


Lenovo LOQ 15IRX10  | €1,149 → €1,499 | PcComponentes | -23.3%
Apple MacBook Air M4 | €899  → €1,179 | PcComponentes | -23.7%
6. Problemas y Tareas Pendientes
🔴 Crítico — Bloquea el análisis
Escasez de datos históricos: Solo hay datos de 1 día (30-03-2026). El análisis de dynamic pricing requiere mínimo 7-14 días de historia acumulada. El crontab lleva inactivo desde esa fecha — verificar si sigue activo con crontab -l.
🟡 Importante — Funcionalidad incompleta
Sin product matching entre días: No hay lógica de fuzzy matching para identificar que "Lenovo LOQ 15IRX10" del día 1 es el mismo producto del día 7. Sin esto, el análisis temporal es imposible.
Dashboard no implementado: El README menciona un dashboard con Dash pero no existe ningún fichero de código para ello.
database.py no existe: Se menciona en la documentación como componente planificado pero no hay fichero.
🟢 Menor — Mejoras pendientes
Validación de calidad de datos (outliers, nulos, errores de encoding)
Evaluar fuente alternativa a MediaMarkt/Idealo
launchd preparado pero no funciona por restricciones TCC de macOS — el crontab es el fallback activo
Resumen ejecutivo para pasar a otra IA
Proyecto: TFG de análisis de dynamic pricing en e-commerce de portátiles.
Estado: Pipeline funcional end-to-end (scraping → ETL → análisis). Scraper operativo en 2 plataformas (PcComponentes y Amazon.es) via Playwright async con plugin Stealth. ETL limpia, normaliza y deduplica los datos. Automatización diaria via crontab a las 09:00. Problema principal: solo hay 1 día de datos históricos; el crontab puede haber dejado de ejecutarse. El siguiente paso crítico es verificar la automatización, acumular historia (≥7 días) e implementar fuzzy matching de productos para