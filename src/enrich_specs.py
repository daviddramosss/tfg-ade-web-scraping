"""
enrich_specs.py

Enriquece los datos del scraper de DOS formas:

1. EXTRACCIÓN DIRECTA: Parsea RAM, CPU, GPU, almacenamiento y pantalla
   directamente del nombre del producto usando regex.
   
2. BENCHMARK KAGGLE: Carga el dataset de Kaggle como referencia
   para análisis comparativo (precio medio por specs en otro mercado).

Uso:
    python3 enrich_specs.py

Input:  /data/processed/precios_portatiles_procesado_*.csv (el más reciente)
Output: /data/processed/dataset_maestro_*.csv
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pandas as pd


# ============================================================================
# RUTAS (ajusta BASE_DIR si tu estructura es diferente)
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
SPECS_DIR = PROCESSED_DIR / "specs"
KAGGLE_DIR = BASE_DIR / "data" / "external" / "kaggle"


# ============================================================================
# 1. EXTRACCIÓN DE SPECS DESDE EL NOMBRE
# ============================================================================

def extract_ram(nombre: str) -> int | None:
    """Extrae GB de RAM del nombre. Ej: '16 GB RAM' → 16"""
    m = re.search(r'(\d+)\s*GB\s*(?:RAM|DDR)', nombre, re.IGNORECASE)
    if m:
        return int(m.group(1))
    # Fallback: buscar patrón "16GB" seguido de algo que no sea SSD/HDD
    m = re.search(r'(\d+)\s*GB(?!\s*SSD|\s*HDD|\s*eMMC|\s*UFS|\s*NVMe)', nombre, re.IGNORECASE)
    if m:
        val = int(m.group(1))
        if val in (4, 6, 8, 12, 16, 24, 32, 64, 128):
            return val
    return None


def extract_storage(nombre: str) -> int | None:
    """Extrae almacenamiento en GB. Ej: '512GB SSD' → 512, '1TB' → 1024"""
    # Buscar TB primero
    m = re.search(r'(\d+)\s*TB', nombre, re.IGNORECASE)
    if m:
        return int(m.group(1)) * 1024
    # Buscar GB SSD/HDD/eMMC/UFS/NVMe
    m = re.search(r'(\d+)\s*GB\s*(?:SSD|HDD|eMMC|UFS|NVMe|almacenamiento)', nombre, re.IGNORECASE)
    if m:
        return int(m.group(1))
    # Fallback: buscar valores típicos de almacenamiento
    m = re.search(r'(\d+)\s*GB', nombre, re.IGNORECASE)
    if m:
        val = int(m.group(1))
        if val in (128, 256, 500, 512, 1000, 1024, 2000, 2048):
            return val
    return None


def extract_cpu(nombre: str) -> str | None:
    """Extrae el procesador. Ej: 'Intel Core i7-14650HX' → 'Intel Core i7-14650HX'"""
    patterns = [
        # Intel Core Ultra (nuevo formato)
        r'((?:Intel\s+)?Core\s+Ultra\s+\d[\s-]\w+)',
        # Intel Core i3/i5/i7/i9 con modelo
        r'((?:Intel\s+)?Core\s+i[3579][\s-]+\w+)',
        # Intel específicos por código
        r'(Intel\s+Core\s+\d\s+\d+\w*)',
        r'(Intel\s+Celeron\s+\w+)',
        r'(Intel\s+N\d+)',
        r'(Intel\s+Pentium\s+\w+)',
        # i7-1355U sin "Intel" delante (PcComponentes)
        r'(?:,\s*)(i[3579][\s-]+\w+)',
        # AMD específicos
        r'(AMD\s+Ryzen\s+(?:AI\s+)?\d[\s-]+\w+)',
        r'(Ryzen\s+(?:AI\s+)?\d[\s-]+\w+)',
        # Apple
        r'(Apple\s+M[1234]\s*(?:Pro|Max|Ultra)?)',
        r'(?<!\w)(M[1234]\s+(?:Pro|Max|Ultra)?(?:\s+\d+\s*[Nn]úcleos)?)',
        # Genéricos
        r'(Celeron\s+\w+)',
        r'(Pentium\s+\w+)',
        r'(Snapdragon\s+\w+)',
    ]
    for pat in patterns:
        m = re.search(pat, nombre, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def extract_gpu(nombre: str) -> str | None:
    """Extrae la GPU. Ej: 'RTX 4060' → 'NVIDIA RTX 4060'"""
    patterns = [
        r'((?:NVIDIA\s+)?(?:GeForce\s+)?RTX\s+\d+\w*)',
        r'((?:NVIDIA\s+)?(?:GeForce\s+)?GTX\s+\d+\w*)',
        r'((?:AMD\s+)?Radeon\s+RX?\s*\d+\w*)',
        r'(Intel\s+(?:Iris\s+)?(?:Xe|UHD|HD)\s*(?:Graphics)?(?:\s+\d+)?)',
        r'(Intel\s+UHD\s+Graphics\s*\d*)',
    ]
    for pat in patterns:
        m = re.search(pat, nombre, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def extract_screen_size(nombre: str) -> float | None:
    """Extrae tamaño de pantalla. Ej: '15.6"' → 15.6"""
    # Buscar formatos: 15.6", 15,6", 15.6 pulgadas
    m = re.search(r'(\d{2}[.,]\d)\s*(?:"|″|pulgadas|Pulgadas)', nombre)
    if m:
        return float(m.group(1).replace(',', '.'))
    # Formato sin decimal: 14", 15", 16", 17"
    m = re.search(r'(\d{2})\s*(?:"|″|pulgadas|Pulgadas)', nombre)
    if m:
        return float(m.group(1))
    return None


def extract_brand(nombre: str) -> str | None:
    """Extrae la marca del producto."""
    # Lista ordenada: marcas largas primero para evitar falsos positivos
    brands = [
        'PcCom', 'PINSTONE', 'Tunhail', 'Primux', 'Innjoo', 'Dynabook',
        'Apple', 'Lenovo', 'Samsung', 'Huawei', 'Microsoft', 'Gigabyte',
        'Medion', 'Razer', 'Toshiba',
        'ASUS', 'Acer', 'Dell', 'BMAX', 'HP', 'MSI',
    ]
    for brand in brands:
        # Buscar como palabra completa para evitar falsos positivos (ej: "LG" en "puLGadas")
        if re.search(r'(?<![a-zA-Z])' + re.escape(brand) + r'(?![a-zA-Z])', nombre, re.IGNORECASE):
            return brand
    return None


def extract_os(nombre: str) -> str | None:
    """Extrae sistema operativo."""
    n = nombre.upper()
    if 'CHROME' in n or 'CHROMEBOOK' in n:
        return 'ChromeOS'
    if 'MACOS' in n or 'MACBOOK' in n or 'APPLE M' in n:
        return 'macOS'
    if 'WINDOWS 11' in n:
        return 'Windows 11'
    if 'WINDOWS' in n:
        return 'Windows'
    if 'LINUX' in n or 'UBUNTU' in n:
        return 'Linux'
    if 'FREEDOS' in n or 'SIN SISTEMA' in n:
        return 'FreeDOS'
    return None


def extract_all_specs(df: pd.DataFrame, name_col: str = "nombre") -> pd.DataFrame:
    """
    Extrae todas las especificaciones del nombre de cada producto.
    Añade columnas: marca, ram_gb, almacenamiento_gb, cpu, gpu,
                    tamanio_pantalla, sistema_operativo
    """
    result = df.copy()

    result['marca'] = result[name_col].apply(extract_brand)
    result['ram_gb'] = result[name_col].apply(extract_ram)
    result['almacenamiento_gb'] = result[name_col].apply(extract_storage)
    result['cpu'] = result[name_col].apply(extract_cpu)
    result['gpu'] = result[name_col].apply(extract_gpu)
    result['tamanio_pantalla'] = result[name_col].apply(extract_screen_size)
    result['sistema_operativo'] = result[name_col].apply(extract_os)

    return result


# ============================================================================
# 2. BENCHMARK KAGGLE (análisis comparativo)
# ============================================================================

def load_kaggle_benchmark(kaggle_dir: Path | None = None) -> pd.DataFrame | None:
    """
    Carga el dataset de Kaggle como benchmark comparativo.
    No cruza con el scraper; se usa para análisis independiente.
    """
    kaggle_dir = kaggle_dir or KAGGLE_DIR

    csv_files = list(kaggle_dir.glob("data.csv")) + list(kaggle_dir.glob("*.csv"))
    if not csv_files:
        print("   ⚠️  No hay dataset Kaggle (opcional, no bloquea el pipeline)")
        return None

    df = pd.read_csv(csv_files[0])

    # Limpiar columnas de índice
    df = df.drop(columns=[c for c in df.columns if 'Unnamed' in c], errors='ignore')

    # Parsear RAM
    df['ram_gb'] = df['Ram'].apply(lambda x: int(re.search(r'(\d+)', str(x)).group(1))
                                   if re.search(r'(\d+)', str(x)) else None)
    # Parsear Storage
    df['almacenamiento_gb'] = df['ROM'].apply(
        lambda x: int(re.search(r'(\d+)', str(x)).group(1))
        if re.search(r'(\d+)', str(x)) else None
    )

    print(f"   ✓ Kaggle benchmark cargado: {len(df)} productos")
    return df


# ============================================================================
# 3. PIPELINE PRINCIPAL
# ============================================================================

def run_enrichment() -> pd.DataFrame:
    """Ejecuta el pipeline completo de enriquecimiento."""

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    SPECS_DIR.mkdir(parents=True, exist_ok=True)

    # ----- Paso 1: Cargar datos del scraper -----
    print("\n[1/4] Cargando datos del scraper...")

    candidates = sorted(PROCESSED_DIR.glob("precios_portatiles_procesado_*.csv"))
    if not candidates:
        raise FileNotFoundError("No hay CSV procesado en /data/processed/")

    latest = candidates[-1]
    df = pd.read_csv(latest)
    print(f"   ✓ Archivo: {latest.name}")
    print(f"   ✓ Registros: {len(df)}")

    # ----- Paso 2: Extraer specs del nombre -----
    print("\n[2/4] Extrayendo especificaciones del nombre...")

    df = extract_all_specs(df, name_col="nombre")

    # Estadísticas de extracción
    total = len(df)
    stats = {
        'marca': df['marca'].notna().sum(),
        'cpu': df['cpu'].notna().sum(),
        'ram_gb': df['ram_gb'].notna().sum(),
        'gpu': df['gpu'].notna().sum(),
        'almacenamiento_gb': df['almacenamiento_gb'].notna().sum(),
        'tamanio_pantalla': df['tamanio_pantalla'].notna().sum(),
        'sistema_operativo': df['sistema_operativo'].notna().sum(),
    }

    for field, count in stats.items():
        pct = count / total * 100
        icon = "✓" if pct >= 50 else "△"
        print(f"   {icon} {field}: {count}/{total} ({pct:.0f}%)")

    # ----- Paso 3: Cargar Kaggle benchmark (opcional) -----
    print("\n[3/4] Cargando benchmark Kaggle...")

    kaggle = load_kaggle_benchmark()

    # ----- Paso 4: Guardar dataset maestro -----
    print("\n[4/4] Guardando dataset maestro...")

    ts = datetime.now().strftime("%Y%m%d_%H%M")
    output = SPECS_DIR / f"dataset_maestro_{ts}.csv"
    df.to_csv(output, index=False)

    print(f"   ✓ Guardado: {output.name}")
    print(f"   ✓ Registros: {len(df)}")
    print(f"   ✓ Columnas: {list(df.columns)}")

    # Guardar Kaggle benchmark aparte si existe
    if kaggle is not None:
        kaggle_output = SPECS_DIR / f"kaggle_benchmark_{ts}.csv"
        kaggle.to_csv(kaggle_output, index=False)
        print(f"   ✓ Benchmark Kaggle: {kaggle_output.name}")

    print(f"\n✅ Pipeline completado.")
    return df


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    result = run_enrichment()

    print("\n📋 Muestra de datos enriquecidos:")
    cols = ['nombre', 'precio_actual_num', 'marca', 'cpu', 'ram_gb', 'gpu', 'almacenamiento_gb']
    cols = [c for c in cols if c in result.columns]
    print(result[cols].head(10).to_string())