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