# TFG ADE — Monitorización de precios de portátiles

**Trabajo de Fin de Grado · Doble Grado Ingeniería Informática + ADE · UCM · 2025-2026**
Autor: David Ramos de Lucas · Tutora: Ana María Sánchez Sánchez

---

## ⚠️ Aviso importante

Este repositorio tiene **finalidad exclusivamente documental**. Contiene el código fuente desarrollado para el TFG y está pensado para que el lector pueda consultar e inspeccionar la implementación técnica descrita en la memoria.

**No está configurado para su ejecución directa**: no se incluyen los datos CSV (almacenados localmente por su tamaño), ni un `requirements.txt`, ni instrucciones de despliegue. Si se desea reproducir el entorno, la memoria describe en detalle el stack tecnológico y las dependencias utilizadas.

---

## Descripción del proyecto

Sistema automatizado de extracción, procesamiento y visualización de precios de portátiles en el mercado español. El pipeline cubre desde la captura diaria de datos en Amazon, PcComponentes y El Corte Inglés hasta su visualización en un cuadro de mando interactivo desarrollado con Dash.

---

## Archivos principales

Estos son los módulos referenciados en la memoria del TFG:

| Archivo | Ubicación | Descripción |
|---|---|---|
| `scraper.py` | `src/` | Extracción de datos con Playwright + playwright-stealth |
| `etl.py` | `src/` | Pipeline ETL: limpieza, normalización y transformación de precios |
| `enrich_specs.py` | `src/` | Enriquecimiento semántico y carga del benchmark de Kaggle |
| `simulate_historical_data.py` | `src/` | Reconstrucción estadística de días con fallos (modelo Ornstein-Uhlenbeck) |
| `matching.py` | `src/` | Product matching entre plataformas mediante similitud difusa |
| `app.py` | `dashboard/` | Cuadro de mando interactivo (Dash + Plotly) |
| `run_daily_pipeline.sh` | `scripts/` | Script de ejecución diaria automatizada |

---

## Estructura del repositorio

```text
scraper/
├── dashboard/
│   └── app.py
├── data/                        # Carpetas de datos (CSVs no incluidos)
│   ├── external/kaggle/
│   ├── processed/
│   │   ├── simulado/
│   │   └── specs/
│   └── raw/
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

---

## Nota sobre los datos

Los archivos CSV generados por el pipeline **no están incluidos** en este repositorio debido a su tamaño. La memoria del TFG describe las características del dataset: 163 modelos únicos de portátiles, recogidos entre el 30 de marzo y el 7 de mayo de 2026, con un total de 2.264 registros distribuidos entre Amazon, PcComponentes y El Corte Inglés.

---

## Stack tecnológico

Python 3.12.8 · Playwright 1.58.0 · Pandas 3.0.1 · Dash 4.1.0 · Plotly 6.6.0 · RapidFuzz · macOS (automatización vía launchd)