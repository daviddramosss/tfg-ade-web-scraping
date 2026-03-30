from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"


def _to_float_eur(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None

    # Normaliza formatos mezclados: "1.299,99€", "399,.99", "899€".
    text = text.replace("€", "").replace("\xa0", "").replace(" ", "")
    text = text.replace(".", "")
    text = text.replace(",.", ".")
    text = text.replace(",", ".")

    try:
        return float(text)
    except ValueError:
        return None


def _compute_discount_pct(precio_actual: float | None, precio_original: float | None) -> float | None:
    if precio_actual is None or precio_original is None:
        return None
    if precio_original <= 0 or precio_original < precio_actual:
        return None
    return round(((precio_original - precio_actual) / precio_original) * 100, 2)


def _normalize_platform(name: object) -> str:
    if name is None:
        return "Desconocida"
    text = str(name).strip().lower()
    if "amazon" in text:
        return "Amazon"
    if "pccomponentes" in text:
        return "PcComponentes"
    if "mediamarkt" in text:
        return "MediaMarkt"
    return str(name).strip() or "Desconocida"


def transform_prices(df: pd.DataFrame) -> pd.DataFrame:
    expected = [
        "nombre",
        "precio_actual",
        "precio_original",
        "descuento",
        "valoracion",
        "plataforma",
        "fecha",
    ]

    for col in expected:
        if col not in df.columns:
            df[col] = None

    out = df[expected].copy()
    out["nombre"] = out["nombre"].astype(str).str.strip()
    out["plataforma"] = out["plataforma"].map(_normalize_platform)

    out["precio_actual_num"] = out["precio_actual"].map(_to_float_eur)
    out["precio_original_num"] = out["precio_original"].map(_to_float_eur)
    out["descuento_pct"] = [
        _compute_discount_pct(a, b)
        for a, b in zip(out["precio_actual_num"], out["precio_original_num"], strict=False)
    ]

    out["fecha_extraccion"] = pd.to_datetime(out["fecha"], errors="coerce")
    out = out.dropna(subset=["nombre", "precio_actual_num", "plataforma", "fecha_extraccion"])

    out = out.drop_duplicates(subset=["nombre", "plataforma", "fecha_extraccion"], keep="last")

    out["anio"] = out["fecha_extraccion"].dt.year
    out["mes"] = out["fecha_extraccion"].dt.month
    out["dia"] = out["fecha_extraccion"].dt.day

    return out.sort_values(["fecha_extraccion", "plataforma", "precio_actual_num"], ascending=[False, True, True])


def process_raw_csv(raw_csv_path: Path | str) -> Path:
    raw_path = Path(raw_csv_path)
    if not raw_path.exists():
        raise FileNotFoundError(f"No existe: {raw_path}")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    df_raw = pd.read_csv(raw_path)
    df_processed = transform_prices(df_raw)

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    output = PROCESSED_DIR / f"precios_portatiles_procesado_{stamp}.csv"
    df_processed.to_csv(output, index=False)
    return output


def process_latest_raw_csv() -> Path:
    candidates = sorted(RAW_DIR.glob("precios_portatiles_*.csv"))
    if not candidates:
        raise FileNotFoundError("No hay CSVs en data/raw")
    return process_raw_csv(candidates[-1])


if __name__ == "__main__":
    path = process_latest_raw_csv()
    print(f"Procesado guardado en: {path}")
