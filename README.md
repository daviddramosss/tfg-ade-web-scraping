# TFG ADE - Monitorizacion de precios de portatiles

Proyecto de TFG orientado a la monitorizacion de precios de portatiles en e-commerce, con pipeline de scraping + ETL + enriquecimiento de especificaciones + dashboard analitico en Dash.

## Objetivo

- Capturar precios de varias plataformas (Amazon, PcComponentes, El Corte Ingles).
- Transformar y normalizar datos para analisis temporal.
- Extracción de datos previos al scrapping con bases de datos reales de precios de portatiles
- Enriquecer productos con especificaciones tecnicas (RAM, CPU, GPU, almacenamiento, pantalla).
- Visualizar tendencias, descuentos y oportunidades en un dashboard interactivo.

## Arquitectura funcional

1. Scraping: genera CSV crudo en data/raw.
2. ETL: limpia y estandariza datos en data/processed.
3. Simulacion historica (opcional): crea archivos con sufijo _0000 para dias anteriores.
4. Enriquecimiento de specs: crea dataset maestro y benchmark Kaggle en data/processed/specs.
5. Dashboard: carga datos procesados de forma recursiva y construye visualizaciones.

## Estructura del proyecto

```text
scraper/
├── dashboard/
│   └── app.py
├── data/
│   ├── external/
│   │   └── kaggle/
│   │       └── data.csv
│   ├── processed/
│   │   ├── simulado/
│   │   │   └── precios_portatiles_procesado_YYYYMMDD_0000.csv
│   │   ├── specs/
│   │   │   ├── dataset_maestro_YYYYMMDD_HHMM.csv
│   │   │   └── kaggle_benchmark_YYYYMMDD_HHMM.csv
│   │   └── precios_portatiles_procesado_YYYYMMDD_HHMM.csv
│   └── raw/
│       └── precios_portatiles_YYYYMMDD_HHMM.csv
├── docs/
├── launchd/
│   └── com.tfg.scraper.daily.plist
├── notebooks/
├── scripts/
│   └── run_daily_pipeline.sh
├── src/
│   ├── scraper.py
│   ├── etl.py
│   ├── simulate_historical_data.py
│   ├── enrich_specs.py
│   ├── ingest_external_dataset.py
│   └── matching.py
├── .gitignore
└── README.md
```

## Requisitos

- Python 3.11 o superior (recomendado).
- macOS/Linux para ejecutar script shell tal cual.
- Dependencias de Python (instalar en entorno virtual):
	- pandas
	- dash
	- dash-bootstrap-components
	- plotly
	- playwright
	- playwright-stealth
	- rapidfuzz
	- numpy

Nota: este repositorio no incluye todavia un requirements.txt. Puedes instalar manualmente o generar uno con pip freeze.

## Puesta en marcha

1. Crear y activar entorno virtual:

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Instalar dependencias base:

```bash
pip install pandas dash dash-bootstrap-components plotly playwright playwright-stealth rapidfuzz numpy
python -m playwright install chromium
```

3. Ejecutar scraping:

```bash
python src/scraper.py
```

4. Ejecutar ETL sobre el ultimo raw:

```bash
python src/etl.py
```

5. Generar historico simulado (opcional):

```bash
python src/simulate_historical_data.py
```

6. Enriquecer especificaciones y generar benchmark:

```bash
python src/enrich_specs.py
```

7. Lanzar dashboard:

```bash
python dashboard/app.py
```

## Flujo diario recomendado

Si quieres ejecutar scraping + ETL en un unico paso:

```bash
bash scripts/run_daily_pipeline.sh
```

El script registra logs en data/raw/pipeline.log.


## Notas del dashboard

- La carga de datos es recursiva dentro de data/processed.
- El dashboard combina datos reales y simulados para series temporales completas.
- Los CSV de specs (dataset_maestro y kaggle_benchmark) se buscan tambien de forma recursiva y con criterio de seleccion para evitar conflictos con archivos legacy.

## Versionado y Git

- No subir datos generados grandes ni entornos virtuales.
- El .gitignore esta configurado para excluir artefactos de scraping, logs y venv.
- Si un archivo ya fue versionado antes de ignorarlo, hay que quitarlo del indice con git rm --cached.

## Ramas recomendadas

- main: version estable para entrega.
- dev: desarrollo diario.

Flujo sugerido:

```bash
git checkout dev
# trabajo diario
git add .
git commit -m "feat: ..."
git push origin dev

git checkout main
git merge dev
git push origin main
git checkout dev
```

## Mejoras futuras sugeridas

- Crear requirements.txt o pyproject.toml para reproducibilidad.
- Añadir tests unitarios para parser de precios y matching.
- Incorporar validaciones de calidad de datos (valores atipicos, nulos criticos).
- Añadir CI en GitHub Actions para lint + test.