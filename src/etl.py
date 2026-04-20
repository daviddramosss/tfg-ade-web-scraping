from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

NOISE_TERMS = {
    "monitor",
    "tablet",
    "impresora",
    "all in one",
    "ipad",
    "tab",
    "multifunción",
    "smart monitor",
}

EXPECTED_COLUMNS = [
    "nombre",
    "precio_actual",
    "precio_original",
    "descuento",
    "valoracion",
    "plataforma",
    "fecha",
]

FINAL_COLUMNS = [
    "nombre",
    "precio_actual",
    "precio_original",
    "descuento",
    "valoracion",
    "plataforma",
    "fecha",
    "precio_actual_num",
    "precio_original_num",
    "descuento_pct",
    "fecha_extraccion",
    "anio",
    "mes",
    "dia",
]


def _to_float_eur(value: object) -> float | None:
    """
    Convierte un valor de precio europeo (formato 1.199,99 €) a float.
    Maneja formatos complejos como 'Precio de venta 1.199,00 €' usando regex.
    """
    if pd.isna(value) or value is None:
        return None

    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None

    match = re.search(r"[\d.,]+", text)
    if not match:
        return None

    numero_str = match.group()
    numero_str = numero_str.replace(".", "").replace(",", ".")

    try:
        return float(numero_str)
    except ValueError:
        return None


def _compute_discount_pct(
    precio_actual: float | None, precio_original: float | None
) -> float | None:
    """Calcula el porcentaje de descuento validando lógica de precios."""
    if precio_actual is None or precio_original is None:
        return None
    if precio_original <= 0 or precio_original < precio_actual:
        return None
    return round(((precio_original - precio_actual) / precio_original) * 100, 2)


def _normalize_platform(name: object) -> str:
    """Normaliza nombres de plataformas a valores estándar."""
    if name is None:
        return "Desconocida"
    text = str(name).strip().lower()
    if "amazon" in text:
        return "Amazon"
    if "pccomponentes" in text:
        return "PcComponentes"
    if "mediamarkt" in text:
        return "MediaMarkt"
    if "elcorteingles" in text or "el corte ingles" in text:
        return "ElCorteIngles"
    return str(name).strip() or "Desconocida"


def _is_laptop(nombre: str) -> bool:
    """
    Verifica que un producto sea un portátil filtrando términos de ruido.
    Retorna False si el nombre contiene palabras clave que indican no-portátil.
    """
    if not isinstance(nombre, str):
        return True

    nombre_lower = nombre.lower()
    return not any(term in nombre_lower for term in NOISE_TERMS)


def transform_prices(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforma y limpia un DataFrame de precios de portátiles.

    Pasos:
    1. Valida y crear columnas esperadas
    2. Normaliza nombres y plataformas
    3. Convierte precios a float
    4. Calcula descuentos
    5. Filtra categoría (solo portátiles)
    6. Elimina duplicados y valores nulos
    7. Extrae componentes de fecha
    8. Valida esquema final

    Args:
        df: DataFrame con columnas de precios crudos

    Returns:
        DataFrame limpio y validado con esquema consistente
    """
    # Asegurar columnas esperadas
    for col in EXPECTED_COLUMNS:
        if col not in df.columns:
            df[col] = None

    out = df[EXPECTED_COLUMNS].copy()

    # Normalizar nombre y plataforma
    out["nombre"] = out["nombre"].astype(str).str.strip()
    out["plataforma"] = out["plataforma"].map(_normalize_platform)

    # Convertir precios
    out["precio_actual_num"] = out["precio_actual"].map(_to_float_eur)
    out["precio_original_num"] = out["precio_original"].map(_to_float_eur)
    out["descuento_pct"] = [
        _compute_discount_pct(a, b)
        for a, b in zip(
            out["precio_actual_num"], out["precio_original_num"], strict=False
        )
    ]

    # Procesar fecha
    out["fecha_extraccion"] = pd.to_datetime(out["fecha"], errors="coerce")

    # Filtro 1: Validar campos críticos
    out = out.dropna(subset=["nombre", "precio_actual_num", "fecha_extraccion"])

    # Filtro 2: Filtrar categoría (solo portátiles)
    out = out[out["nombre"].apply(_is_laptop)].copy()

    # Filtro 3: Eliminar duplicados
    out = out.drop_duplicates(
        subset=["nombre", "plataforma", "fecha_extraccion"], keep="last"
    )

    # Extraer componentes de fecha
    out["anio"] = out["fecha_extraccion"].dt.year
    out["mes"] = out["fecha_extraccion"].dt.month
    out["dia"] = out["fecha_extraccion"].dt.day

    # Validar esquema final
    for col in FINAL_COLUMNS:
        if col not in out.columns:
            raise ValueError(f"Columna faltante en resultado: {col}")

    out = out[FINAL_COLUMNS]

    return out.sort_values(
        ["fecha_extraccion", "plataforma", "precio_actual_num"],
        ascending=[False, True, True],
    )


def process_raw_csv(raw_csv_path: Path | str) -> Path:
    """
    Procesa un archivo CSV crudo, lo transforma y guarda en data/processed.

    Args:
        raw_csv_path: Ruta al archivo CSV crudo

    Returns:
        Path al archivo procesado generado

    Raises:
        FileNotFoundError: Si el archivo no existe
    """
    raw_path = Path(raw_csv_path)
    if not raw_path.exists():
        raise FileNotFoundError(f"No existe: {raw_path}")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    df_raw = pd.read_csv(raw_path)
    filas_crudas = len(df_raw)

    df_processed = transform_prices(df_raw)
    filas_procesadas = len(df_processed)

    print(f"✓ Filas crudas: {filas_crudas}")
    print(f"✓ Filas procesadas: {filas_procesadas}")
    print(f"✓ Filas filtradas: {filas_crudas - filas_procesadas}")

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    output = PROCESSED_DIR / f"precios_portatiles_procesado_{stamp}.csv"
    df_processed.to_csv(output, index=False)

    return output


def process_latest_raw_csv() -> Path:
    """
    Procesa el archivo CSV crudo más reciente en data/raw.

    Returns:
        Path al archivo procesado generado

    Raises:
        FileNotFoundError: Si no hay archivos en data/raw
    """
    candidates = sorted(RAW_DIR.glob("precios_portatiles_*.csv"))
    if not candidates:
        raise FileNotFoundError("No hay CSVs en data/raw")
    return process_raw_csv(candidates[-1])


if __name__ == "__main__":
    path = process_latest_raw_csv()
    print(f"\n✓ Procesado guardado en: {path}")