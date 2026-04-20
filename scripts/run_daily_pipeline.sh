#!/bin/bash

# Ruta absoluta al proyecto
PROJECT="/Users/david/Documents/scraper"

# Activar entorno virtual
source "$PROJECT/venv/bin/activate"

# Ejecutar scraper
echo "[$(date)] Iniciando scraping..." >> "$PROJECT/data/raw/pipeline.log"
python "$PROJECT/src/scraper.py" >> "$PROJECT/data/raw/pipeline.log" 2>&1

# Ejecutar ETL
echo "[$(date)] Iniciando ETL..." >> "$PROJECT/data/raw/pipeline.log"
python "$PROJECT/src/etl.py" >> "$PROJECT/data/raw/pipeline.log" 2>&1

echo "[$(date)] Pipeline completado." >> "$PROJECT/data/raw/pipeline.log"