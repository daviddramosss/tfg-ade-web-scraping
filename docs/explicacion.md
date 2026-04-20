# Explicación completa del proyecto — TFG Dynamic Pricing

Fecha de redacción: 2026-04-20  
Rama activa: `dev`

---

## 1. Objetivo final del proyecto

El TFG investiga el **dynamic pricing en el e-commerce español de portátiles**: ¿cambian los precios entre plataformas? ¿con qué frecuencia? ¿qué patrones hay entre Amazon y PcComponentes?

Para responder eso, el proyecto necesita:

1. Recoger precios de forma automática y diaria.
2. Limpiar y normalizar esos datos.
3. Identificar el mismo producto en distintos días y plataformas.
4. Visualizar la evolución temporal en un dashboard.
5. Sacar conclusiones estadísticas y redactarlas en la memoria del TFG.

---

## 2. Estructura de carpetas

```
scraper/
├── src/                         # Código fuente principal
│   ├── scraper.py               # Extrae precios de la web
│   ├── etl.py                   # Limpia y normaliza los datos
│   ├── matching.py              # Identifica el mismo producto entre días/plataformas
│   └── ingest_external_dataset.py  # Incorpora CSVs externos (Kaggle u otras fuentes)
│
├── data/
│   ├── raw/                     # CSVs crudos tal como salen del scraper
│   └── processed/               # CSVs listos para análisis
│
├── notebooks/
│   ├── pruebas_scraping_fuentes.ipynb   # Diagnóstico técnico de fuentes y anti-bot
│   └── analisis_temporal_tfg.ipynb      # Análisis estadístico y gráficos
│
├── dashboard/                   # (pendiente) Dashboard Plotly Dash
│   └── app.py
│
├── scripts/
│   └── run_daily_pipeline.sh    # Script bash que lanza scraper + ETL
│
├── launchd/
│   └── com.tfg.scraper.daily.plist  # Configuración macOS para ejecución automática
│
├── docs/
│   ├── estado.md                # Historial de decisiones técnicas
│   ├── estado2.md               # Continuación del historial
│   └── explicacion.md           # Este archivo
│
├── venv/                        # Entorno virtual Python (no subir a git)
└── README.md                    # Estructura básica del repositorio
```

---

## 3. Qué hace cada archivo

### `src/scraper.py`

Es el **motor de extracción**. Usa Playwright (un navegador automatizado) con la
extensión `playwright-stealth` para evitar los detectores anti-bot.

- Abre Chromium en modo headless (sin ventana visible).
- Navega a `pccomponentes.com/portatiles` y `amazon.es/s?k=portatiles`.
- Extrae de cada tarjeta de producto: nombre, precio actual, precio original y valoración.
- Guarda todo en `data/raw/precios_portatiles_YYYYMMDD_HHMM.csv`.
- Ejecutarlo directamente: `python src/scraper.py`

Lo más importante de este archivo es la configuración `ScrapeConfig`:
- `max_items_per_platform = 40` — cuántos productos por tienda.
- `headless = True` — sin ventana visible; ponlo en `False` para depurar.

### `src/etl.py`

Es el **pipeline de limpieza**. Toma un CSV crudo y lo transforma en datos listos para analizar.

Hace estas operaciones:
- Normaliza precios: convierte `"1.299,99€"`, `"1299.99"`, `"1.299€"` al mismo float.
- Calcula `descuento_pct` cuando hay precio original.
- Normaliza nombres de plataforma (p.ej. `"amazon"` → `"Amazon"`).
- Elimina filas sin nombre, sin precio o sin fecha.
- Deduplica: si el mismo producto aparece dos veces en la misma extracción, se queda con el último.
- Extrae año, mes y día como columnas separadas.
- Guarda en `data/processed/precios_portatiles_procesado_YYYYMMDD_HHMM.csv`.
- Ejecutarlo directamente: `python src/etl.py` (procesa el CSV más reciente de `raw/`)

### `src/matching.py`

Es el **motor de identidad de productos**. Resuelve el problema central del TFG:
el mismo portátil se llama diferente en Amazon y PcComponentes.

Metodología (entity resolution en dos etapas):

1. **Normalización**: elimina tildes, palabras genéricas ("Portátil", "Windows",
   "Negro"), signos de puntuación y espacios extra.
2. **Guarda de especificaciones**: extrae marca, RAM y almacenamiento con regex.
   Si dos productos tienen RAM diferente (16 GB vs 32 GB), se descarta la comparación.
3. **Similaridad fuzzy**:
   - Mismo platform → `token_sort_ratio` (umbral ≥ 88)
   - Plataformas distintas → `token_set_ratio` (umbral ≥ 82, más tolerante al
     orden de palabras distinto entre catálogos)
4. **Clustering Union-Find**: agrupación transitiva — si A≃B y B≃C, los tres
   comparten el mismo `producto_id` aunque A y C no superen el umbral directamente.

El resultado es una columna `producto_id` que permite trazar la evolución de precio
de un modelo concreto a lo largo del tiempo y entre plataformas.

Uso:
```python
from src.matching import build_product_id, match_across_files

# Sobre un solo DataFrame ya procesado
df = build_product_id(df_procesado)

# Sobre múltiples archivos de días distintos
from pathlib import Path
import pandas as pd
dfs = [pd.read_csv(f) for f in sorted(Path("data/processed").glob("*.csv"))]
combined = match_across_files(dfs)
```

### `src/ingest_external_dataset.py`

Utilidad para incorporar un **CSV externo** (por ejemplo de Kaggle) al mismo
esquema de columnas que usa el resto del pipeline. Útil como fuente alternativa
si el scraping de alguna plataforma falla o como enriquecimiento histórico.

Uso:
```python
from src.ingest_external_dataset import ingest_kaggle_csv
ingest_kaggle_csv("ruta/al/dataset.csv", platform_name="Kaggle")
```

### `scripts/run_daily_pipeline.sh`

Script bash que encadena los dos pasos principales:
1. Activa el entorno virtual.
2. Ejecuta `scraper.py` → genera CSV en `raw/`.
3. Ejecuta `etl.py` → genera CSV en `processed/`.
4. Registra todo en `data/raw/pipeline.log`.

Se ejecuta automáticamente cada día a las 09:00 vía `crontab`.

### `launchd/com.tfg.scraper.daily.plist`

Alternativa a crontab para automatización en macOS. Actualmente inactiva
(por restricciones TCC de macOS sobre la carpeta `Documents`); el cron es el
método activo.

### `notebooks/pruebas_scraping_fuentes.ipynb`

Notebook de diagnóstico técnico. Contiene:
- Pruebas de acceso HTTP con requests/BeautifulSoup (descartadas por anti-bot).
- Diagnóstico de Playwright síncrono en Jupyter (descartado por incompatibilidad).
- Verificación del uso correcto de `playwright-stealth`.
- Prueba de Idealo (bloqueada por Akamai, descartada).
- Ejecución manual del pipeline y visualización del DataFrame resultante.

Es evidencia metodológica para la memoria del TFG, no código de producción.

### `notebooks/analisis_temporal_tfg.ipynb`

Notebook de **análisis estadístico**. Contiene los gráficos y métricas que irán
a la memoria. Actualmente con datos preliminares:
- 49 observaciones analizadas.
- Precio medio Amazon: 431 EUR / PcComponentes: 957 EUR.
- Se espera que al acumular más días la variación temporal sea más rica.

---

## 4. Flujo completo del proyecto

```
┌─────────────────────────────────────────────┐
│  CADA DÍA A LAS 09:00 (crontab)             │
│                                             │
│  run_daily_pipeline.sh                      │
│       │                                     │
│       ▼                                     │
│  scraper.py  ──────►  data/raw/             │
│  (Playwright + Stealth)   precios_YYYYMMDD  │
│       │                   _HHMM.csv         │
│       ▼                                     │
│  etl.py  ──────────►  data/processed/       │
│  (limpieza,               precios_procesado │
│   normalización)          _YYYYMMDD_HHMM.csv│
└─────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────┐
│  ANÁLISIS (manual, en notebook o dashboard) │
│                                             │
│  matching.py                                │
│  (asigna producto_id igual a mismo portátil │
│   en distintos días y plataformas)          │
│       │                                     │
│       ▼                                     │
│  analisis_temporal_tfg.ipynb                │
│  (gráficos de evolución de precios,         │
│   comparativa entre plataformas,            │
│   detección de patrones de descuento)       │
│       │                                     │
│       ▼                                     │
│  dashboard/app.py  (PENDIENTE)              │
│  (visualización interactiva con Plotly Dash)│
└─────────────────────────────────────────────┘
```

---

## 5. Qué tenemos ahora mismo

| Componente | Estado |
|---|---|
| Scraping Amazon | Funcional |
| Scraping PcComponentes | Funcional |
| Scraping MediaMarkt | Bloqueado (anti-bot), descartado |
| ETL / limpieza | Funcional |
| Automatización diaria (cron) | Activa (09:00) |
| Matching de productos | Implementado, pendiente de validar con datos reales |
| Análisis temporal | En progreso (notebook con datos preliminares) |
| Dashboard | Pendiente de implementar |
| Fuente externa (Kaggle) | Módulo preparado, no usado aún |

Datos acumulados:
- Varios snapshots entre marzo y abril 2026.
- ~40 productos por plataforma por día = ~80 filas por snapshot.
- Aún pocos días para ver variación temporal clara; mejorará con el tiempo.

---

## 6. Qué falta para el objetivo final

En orden de prioridad:

### 6.1 Acumular más datos (automático, no requiere código)
El cron ya corre. Simplemente dejar que pasen semanas para tener una serie
temporal con variación real.

### 6.2 Integrar `matching.py` en el análisis
El módulo ya existe pero no está conectado al notebook de análisis. Hay que:
```python
# En analisis_temporal_tfg.ipynb
from src.matching import match_across_files
from pathlib import Path
import pandas as pd

dfs = [pd.read_csv(f) for f in sorted(Path("data/processed").glob("*.csv"))]
combined = match_across_files(dfs)
# Ahora combined tiene producto_id: puedes agrupar por producto y ver evolución de precio
```

### 6.3 Dashboard (`dashboard/app.py`)
La carpeta existe pero está vacía. Un dashboard mínimo en Plotly Dash necesita:
- Selector de producto (`producto_id` + nombre).
- Gráfico de línea: precio a lo largo del tiempo, una línea por plataforma.
- Tabla comparativa de precio actual entre plataformas.

### 6.4 Análisis estadístico formal
Para la memoria del TFG:
- Estadísticos descriptivos por plataforma (media, mediana, desviación).
- Test de diferencia de precios entre plataformas (t-test o Mann-Whitney).
- Análisis de frecuencia y magnitud de cambios de precio.
- Identificación de productos con mayor variabilidad.

### 6.5 Fuente de datos alternativa (opcional)
Si se quiere enriquecer el histórico desde el inicio, buscar un dataset de Kaggle
con precios de portátiles españoles e incorporarlo con `ingest_external_dataset.py`.

---

## 7. Cómo ejecutar el proyecto manualmente

### Requisitos previos (una sola vez)

```bash
# Desde la carpeta del proyecto
source venv/bin/activate

# Instalar dependencias (si no están)
pip install playwright rapidfuzz pandas dash
playwright install chromium
```

### Ejecución paso a paso

```bash
# 1. Activar entorno virtual
source venv/bin/activate

# 2. Scraping (genera CSV en data/raw/)
python src/scraper.py

# 3. ETL (limpia el CSV más reciente y guarda en data/processed/)
python src/etl.py

# 4. Matching (desde Python o notebook)
python -c "
from pathlib import Path
import pandas as pd
from src.matching import match_across_files

dfs = [pd.read_csv(f) for f in sorted(Path('data/processed').glob('*.csv'))]
combined = match_across_files(dfs)
print(combined[['nombre','plataforma','producto_id','precio_actual_num']].head(20))
"

# 5. Abrir notebook de análisis
jupyter notebook notebooks/analisis_temporal_tfg.ipynb
```

### Verificar que la automatización diaria funciona

```bash
# Ver las últimas líneas del log del pipeline automático
tail -30 data/raw/pipeline.log

# Ver qué archivos se han generado
ls -lt data/raw/*.csv
ls -lt data/processed/*.csv
```

### Ejecutar el pipeline completo manualmente (igual que lo hace el cron)

```bash
bash scripts/run_daily_pipeline.sh
```

---

## 8. Ramas de git

| Rama | Uso |
|---|---|
| `main` | Solo código que funciona y está revisado. Lo que se presenta. |
| `dev` | Trabajo del día a día (rama actual). |

Cuando termines una fase funcional (dashboard, análisis final):
```bash
git checkout main
git merge dev
git push origin main
git checkout dev
```

---

## 9. Dependencias Python

Instaladas en `venv/`:

| Paquete | Para qué se usa |
|---|---|
| `playwright` | Navegador automatizado para scraping |
| `playwright-stealth` | Evitar detección anti-bot |
| `pandas` | Manipulación de datos y CSVs |
| `rapidfuzz` | Similaridad fuzzy para matching de productos |
| `dash` + `plotly` | Dashboard interactivo (pendiente) |
| `jupyter` | Notebooks de análisis |
| `beautifulsoup4` | Parseo HTML (usado en pruebas previas) |
