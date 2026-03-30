# tfg-ade-web-scraping

Estructura de carpetas

scraper/
│
├── venv/                  # Entorno virtual (no tocar, no subir)
│
├── data/
│   ├── raw/               # Datos tal como salen del scraper (CSV, SQLite)
│   └── processed/         # Datos ya limpios tras el ETL
│
├── notebooks/             # Tus Jupyter Notebooks de análisis y pruebas
│
├── src/                   # El código fuente principal
│   ├── scraper.py         # El scraper
│   ├── etl.py             # El pipeline ETL
│   └── database.py        # Gestión de la base de datos SQLite
│
├── dashboard/             # El código del dashboard Plotly Dash
│   └── app.py
│
├── .gitignore             # Ya existe, está bien
└── README.md              # Ya existe

La idea es: notebooks para explorar y probar, src para el código definitivo y limpio.

En cuanto a las ramas
main → Solo código que funciona y está revisado. Lo que subiré a presentar.
dev → Donde trabajo el día a día.

A partir de ahora trabajas siempre en dev. Cuando termines una fase funcional (el scraper completo, el ETL, el dashboard), haces un merge a main:
bashgit checkout main
git merge dev
git push origin main
git checkout dev