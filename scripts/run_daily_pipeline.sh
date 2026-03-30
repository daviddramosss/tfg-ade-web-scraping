#!/bin/zsh
set -euo pipefail

PROJECT_DIR="/Users/david/Documents/scraper"
PYTHON_BIN="/Users/david/Documents/scraper/venv/bin/python"
LOG_DIR="$PROJECT_DIR/data/raw"

cd "$PROJECT_DIR"

# 1) Scraping diario
"$PYTHON_BIN" src/scraper.py >> "$LOG_DIR/pipeline.log" 2>&1

# 2) ETL diario
"$PYTHON_BIN" src/etl.py >> "$LOG_DIR/pipeline.log" 2>&1
