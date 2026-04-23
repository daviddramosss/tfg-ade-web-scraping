#!/bin/bash

set -euo pipefail

# Ruta absoluta al proyecto
PROJECT="/Users/david/Documents/scraper"
PYTHON="$PROJECT/venv/bin/python"
LOG_FILE="$PROJECT/data/raw/pipeline.log"

if [[ ! -x "$PYTHON" ]]; then
	echo "No se encuentra el Python del entorno virtual: $PYTHON" >&2
	exit 1
fi

# Ejecutar scraper
echo "[$(date)] Iniciando scraping..." | tee -a "$LOG_FILE"
"$PYTHON" "$PROJECT/src/scraper.py" 2>&1 | tee -a "$LOG_FILE"
latest_raw=$(ls -t "$PROJECT"/data/raw/precios_portatiles_*.csv | head -n 1)
echo "[$(date)] CSV crudo generado: $latest_raw" | tee -a "$LOG_FILE"

# Ejecutar ETL
echo "[$(date)] Iniciando ETL..." | tee -a "$LOG_FILE"
"$PYTHON" "$PROJECT/src/etl.py" 2>&1 | tee -a "$LOG_FILE"
latest_processed=$(ls -t "$PROJECT"/data/processed/precios_portatiles_procesado_*.csv | head -n 1)
echo "[$(date)] CSV procesado generado: $latest_processed" | tee -a "$LOG_FILE"

# Ejecutar enriquecimiento de especificaciones
echo "[$(date)] Iniciando enriquecimiento de specs..." | tee -a "$LOG_FILE"
"$PYTHON" "$PROJECT/src/enrich_specs.py" 2>&1 | tee -a "$LOG_FILE"
latest_dataset=$(ls -t "$PROJECT"/data/processed/specs/dataset_maestro_*.csv | head -n 1)
latest_benchmark=$(ls -t "$PROJECT"/data/processed/specs/kaggle_benchmark_*.csv | head -n 1)
echo "[$(date)] CSV maestro generado: $latest_dataset" | tee -a "$LOG_FILE"
echo "[$(date)] CSV benchmark generado: $latest_benchmark" | tee -a "$LOG_FILE"

echo "[$(date)] Pipeline completado." | tee -a "$LOG_FILE"