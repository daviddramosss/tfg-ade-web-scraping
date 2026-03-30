from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"


def ingest_kaggle_csv(
    source_csv: str | Path,
    platform_name: str = "DatasetPublico",
    name_col: str = "nombre",
    price_col: str = "precio_actual",
) -> Path:
    src = Path(source_csv)
    if not src.exists():
        raise FileNotFoundError(f"No existe el fichero: {src}")

    df = pd.read_csv(src)
    if name_col not in df.columns or price_col not in df.columns:
        raise ValueError(
            "El CSV debe incluir al menos las columnas configuradas para nombre y precio."
        )

    out = pd.DataFrame(
        {
            "nombre": df[name_col].astype(str).str.strip(),
            "precio_actual": df[price_col],
            "precio_original": None,
            "descuento": None,
            "valoracion": None,
            "plataforma": platform_name,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
    )

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    output = RAW_DIR / f"dataset_externo_{platform_name.lower()}_{stamp}.csv"
    out.to_csv(output, index=False)
    return output


if __name__ == "__main__":
    print(
        "Uso: importa ingest_kaggle_csv desde notebook o scripts y pásale la ruta del CSV externo."
    )
