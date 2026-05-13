
from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================================
# CONFIGURACIÓN
# ============================================================================

PROCESSED_DIR = Path("data/processed")

# Rango de fechas a simular 
START_DATE = datetime(2026, 4, 1)
END_DATE = datetime(2026, 4, 4)  

# Seed para reproducibilidad 
random.seed(42)
np.random.seed(42)


# ============================================================================
# MODELO DE SIMULACIÓN DE PRECIOS
# ============================================================================

def simulate_price_series(
    precio_base: float,
    precio_original: float | None,
    plataforma: str,
    n_days: int,
) -> list[float]:
    """
    Genera una serie de precios diarios simulada con comportamiento realista.

    Parámetros del modelo:
      - Amazon: volatilidad alta (repricing frecuente), rango ±3%
      - PcComponentes: volatilidad media, ofertas semanales, rango ±2%
      - El Corte Inglés: volatilidad baja, precios más estables, rango ±1%

    Eventos añadidos:
      - 1-2 "promos" aleatorias en el mes (-5% a -15% durante 2-4 días)
      - Suelo al 85% del precio base
      - Techo al 110% del precio base
    """
    # Volatilidad diaria por plataforma (desviación estándar del paseo aleatorio)
    volatility = {
        "Amazon": 0.008,          # 0.8% diario
        "PcComponentes": 0.005,   # 0.5% diario
        "ElCorteIngles": 0.003,   # 0.3% diario
    }.get(plataforma, 0.005)

    # Tendencia: ligera deriva hacia el precio final (convergencia)
    # Empezamos un 2-5% por encima del precio base y convergemos hacia él
    starting_multiplier = random.uniform(1.02, 1.05)
    precio_inicio = precio_base * starting_multiplier

    # Paseo aleatorio con reversión a la media (Ornstein-Uhlenbeck simplificado)
    precios = []
    precio_actual = precio_inicio
    reversion_speed = 0.08  # Qué tan fuerte tiende al precio base

    for day in range(n_days):
        # Componente de reversión a la media
        drift = reversion_speed * (precio_base - precio_actual) / precio_base
        # Componente aleatorio
        noise = np.random.normal(0, volatility)
        # Actualizar precio
        precio_actual = precio_actual * (1 + drift + noise)
        # Aplicar suelo y techo
        precio_actual = max(precio_base * 0.85, min(precio_base * 1.10, precio_actual))
        precios.append(precio_actual)

    # Añadir 1-2 eventos promocionales puntuales
    num_promos = random.choice([0, 1, 1, 2])  # Sesgado a 1 promo/mes
    for _ in range(num_promos):
        promo_start = random.randint(2, n_days - 4)
        promo_duration = random.randint(2, 4)
        promo_depth = random.uniform(0.05, 0.15)  # 5-15% descuento
        for d in range(promo_start, min(promo_start + promo_duration, n_days)):
            precios[d] = precios[d] * (1 - promo_depth)

    # Redondear a 2 decimales
    return [round(p, 2) for p in precios]


# ============================================================================
# GENERACIÓN DE HISTÓRICO
# ============================================================================

def load_real_products() -> pd.DataFrame:
    """Carga el último CSV procesado real como plantilla de productos."""
    files = sorted(PROCESSED_DIR.glob("precios_portatiles_procesado_*.csv"))
    # Filtrar los que puedan haber sido ya simulados
    real_files = [f for f in files if not _is_simulated_file(f)]

    if not real_files:
        raise FileNotFoundError(
            "No se encontró CSV procesado real en /data/processed/"
        )

    latest = real_files[-1]
    print(f"📂 Usando como plantilla: {latest.name}")
    return pd.read_csv(latest)


def _is_simulated_file(path: Path) -> bool:
    """Detecta si un archivo es una simulación previa por su hora (_0000)."""
    return "_0000.csv" in path.name


def generate_historical_data() -> None:
    """Genera un CSV por día desde START_DATE hasta END_DATE."""

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Cargar productos reales como plantilla
    df_real = load_real_products()
    print(f"📊 Productos plantilla: {len(df_real)}")

    # Número total de días a simular
    n_days = (END_DATE - START_DATE).days + 1
    print(f"📅 Días a simular: {n_days} (del {START_DATE.date()} al {END_DATE.date()})")

    # Simular serie completa de precios para cada producto
    print("\n🔄 Generando series temporales...")
    price_series_by_product = {}
    for idx, row in df_real.iterrows():
        precio_base = row["precio_actual_num"]
        precio_original = row.get("precio_original_num")
        plataforma = row["plataforma"]

        if pd.isna(precio_base):
            continue

        series = simulate_price_series(
            precio_base=precio_base,
            precio_original=precio_original,
            plataforma=plataforma,
            n_days=n_days,
        )
        price_series_by_product[idx] = series

    # Generar un CSV por día
    print(f"\n💾 Guardando {n_days} CSVs...")
    for day_offset in range(n_days):
        current_date = START_DATE + timedelta(days=day_offset)
        day_rows = []

        for idx, row in df_real.iterrows():
            if idx not in price_series_by_product:
                continue

            precio_hoy = price_series_by_product[idx][day_offset]
            precio_orig = row.get("precio_original_num")

            # Calcular descuento si hay precio original
            if pd.notna(precio_orig) and precio_orig > precio_hoy:
                dto_pct = round(((precio_orig - precio_hoy) / precio_orig) * 100, 2)
            else:
                dto_pct = None

            # Formatos tipo scraper original
            fecha_str = current_date.strftime("%Y-%m-%d 00:00")
            fecha_ext = current_date.strftime("%Y-%m-%d 00:00:00")

            day_rows.append({
                "nombre": row["nombre"],
                "precio_actual": f"{precio_hoy:.2f}".replace(".", ",") + "€",
                "precio_original": (f"{precio_orig:.2f}".replace(".", ",") + "€"
                                    if pd.notna(precio_orig) else ""),
                "descuento": f"-{int(dto_pct)}%" if dto_pct and dto_pct > 0 else "",
                "valoracion": row.get("valoracion", ""),
                "plataforma": row["plataforma"],
                "fecha": fecha_str,
                "enlace": row.get("enlace", ""),
                "precio_actual_num": precio_hoy,
                "precio_original_num": precio_orig if pd.notna(precio_orig) else None,
                "descuento_pct": dto_pct,
                "fecha_extraccion": fecha_ext,
                "anio": current_date.year,
                "mes": current_date.month,
                "dia": current_date.day,
                "es_simulado": True,  # ← MARCADOR CLAVE
            })

        df_day = pd.DataFrame(day_rows)
        file_name = f"precios_portatiles_procesado_{current_date.strftime('%Y%m%d')}_0000.csv"
        file_path = PROCESSED_DIR / file_name
        df_day.to_csv(file_path, index=False)

    print(f"\n✅ Completado: {n_days} archivos generados")
    print(f"   Ubicación: {PROCESSED_DIR}")
    print(f"\n⚠️  TODOS los datos simulados tienen es_simulado=True")
    print(f"   Los datos reales de tu scraper NO tienen esa columna (o es False)")


if __name__ == "__main__":
    generate_historical_data()
    print("\n🔄 Reinicia tu dashboard (app.py) para ver el histórico completo.")