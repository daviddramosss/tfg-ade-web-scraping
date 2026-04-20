"""
Product matching module — identifies the same laptop across scrape dates and platforms.

Methodology (entity resolution, two-stage):
  1. Normalisation: remove diacritics, stopwords and noise so "Portátil Lenovo
     IdeaPad Slim 3 15IRH10 15,3\" Intel Core i5" and the same title on Amazon
     reduce to a comparable form.
  2. Spec guard: extract RAM, storage and brand from each name. If two products
     share an extractable spec that differs (e.g. 16 GB vs 32 GB) they cannot
     be the same unit, preventing high-similarity false positives.
  3. Fuzzy similarity:
       • Same platform  → token_sort_ratio  (threshold ≥ 88): tolerates minor
         ordering differences within one catalogue.
       • Cross-platform → token_set_ratio   (threshold ≥ 82): tolerates the
         richer variation between Amazon and PcComponentes titles (extra words,
         marketing suffixes, different attribute order).
     token_sort/set_ratio are standard choices in the product-matching literature
     (Köpcke & Rahm, 2010; Mudgal et al., 2018) because they are insensitive to
     word order, a common source of variation in e-commerce titles.
  4. Union-Find transitive clustering: if A≃B and B≃C then A, B, C share one
     `producto_id` even if A and C individually fall below the threshold.

Complexity: O(n²) comparisons — acceptable for the ~200 products per scrape in
this TFG. For larger catalogues, a blocking step (same brand + screen size) would
reduce the candidate pairs before fuzzy comparison.

Dependencies:
    pip install rapidfuzz
"""

from __future__ import annotations

import re
import unicodedata

import pandas as pd
from rapidfuzz import fuzz


# ---------------------------------------------------------------------------
# 1. Text normalisation
# ---------------------------------------------------------------------------

_STOPWORDS = re.compile(
    r"\b(portatil|laptop|notebook|ordenador|"
    r"windows|home|pro|professional|edition|"
    r"negro|plata|gris|blanco|azul|rojo|"
    r"wi.?fi|bluetooth|hdmi|thunderbolt|"
    r"rgb|e.shutter)\b",
    re.IGNORECASE,
)

_NOISE = re.compile(r'["""\'´`()\[\]{}|\\@#$%^&*+=<>?/]')


def normalize_name(name: str) -> str:
    """Return a cleaned, lowercase, diacritic-free version of a product name."""
    text = unicodedata.normalize("NFD", name)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower()
    text = _NOISE.sub(" ", text)
    text = _STOPWORDS.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------------------------------------------------------------------------
# 2. Spec extraction & compatibility guard
# ---------------------------------------------------------------------------

_BRAND = re.compile(
    r"\b(apple|asus|acer|dell|hp|lenovo|msi|samsung|huawei|lg|razer|"
    r"microsoft|toshiba|fujitsu|medion|alurin|pccom|chuwi)\b",
    re.IGNORECASE,
)

# RAM: a bare "NGB" before a slash or space, or explicitly tagged DDR/LPDDR.
# Excludes VRAM patterns like "RTX 4060 8GB" by requiring the GB to precede
# a slash, SSD keyword, or DDR qualifier — not follow a GPU name.
_RAM = re.compile(
    r"(?<![a-z])(\d+)\s*gb\s*(?:ddr\d*|lpddr\d*|ram\b|(?=[/\s](?:\d|ssd|nvme)))",
    re.IGNORECASE,
)
_STORAGE = re.compile(r"(\d+)\s*(gb|tb)\s*(?:ssd|nvme|m\.?2)", re.IGNORECASE)
_SCREEN = re.compile(r'(\d+(?:[.,]\d+)?)\s*(?:"|″|")', re.IGNORECASE)


def _extract_specs(name: str) -> dict:
    specs: dict[str, object] = {}

    m = _BRAND.search(name)
    specs["brand"] = m.group(1).lower() if m else None

    m = _RAM.search(name)
    specs["ram_gb"] = int(m.group(1)) if m else None

    m = _STORAGE.search(name)
    if m:
        val, unit = int(m.group(1)), m.group(2).lower()
        specs["storage_gb"] = val * 1024 if unit == "tb" else val
    else:
        specs["storage_gb"] = None

    m = _SCREEN.search(name)
    specs["screen_inch"] = float(m.group(1).replace(",", ".")) if m else None

    return specs


def _specs_compatible(a: dict, b: dict) -> bool:
    """
    Return False only when two products share an extractable spec that clearly
    differs. Unknown (None) specs are treated as compatible.

    Screen size is intentionally excluded: free-text titles frequently round or
    omit decimals (e.g. "13\"" for a 13.6" panel), producing false negatives
    more often than it catches true conflicts.
    """
    for key in ("brand", "ram_gb", "storage_gb"):
        va, vb = a.get(key), b.get(key)
        if va is not None and vb is not None and va != vb:
            return False
    return True


# ---------------------------------------------------------------------------
# 3. Union-Find (path-compressed) for transitive cluster closure
# ---------------------------------------------------------------------------

class _UnionFind:
    def __init__(self, n: int) -> None:
        self._p = list(range(n))

    def find(self, x: int) -> int:
        while self._p[x] != x:
            self._p[x] = self._p[self._p[x]]
            x = self._p[x]
        return x

    def union(self, x: int, y: int) -> None:
        self._p[self.find(x)] = self.find(y)


# ---------------------------------------------------------------------------
# 4. Public API
# ---------------------------------------------------------------------------

SAME_PLATFORM_THRESHOLD = 88
CROSS_PLATFORM_THRESHOLD = 82


def build_product_id(
    df: pd.DataFrame,
    same_platform_threshold: int = SAME_PLATFORM_THRESHOLD,
    cross_platform_threshold: int = CROSS_PLATFORM_THRESHOLD,
) -> pd.DataFrame:
    """
    Assign a ``producto_id`` integer to each row.

    Rows that refer to the same physical laptop — possibly listed on different
    platforms or scraped on different dates — receive the same ``producto_id``.

    Parameters
    ----------
    df:
        DataFrame containing at least ``nombre`` and ``plataforma`` columns.
    same_platform_threshold:
        Minimum token_sort_ratio score (0–100) to merge two listings from the
        same platform.
    cross_platform_threshold:
        Minimum token_set_ratio score (0–100) to merge listings from different
        platforms.

    Returns
    -------
    df with a new ``producto_id`` column (int64, 0-indexed cluster labels).
    """
    if df.empty:
        return df.assign(producto_id=pd.array([], dtype="int64"))

    names = df["nombre"].astype(str).tolist()
    platforms = df["plataforma"].astype(str).tolist()
    normalized = [normalize_name(n) for n in names]
    specs = [_extract_specs(n) for n in names]
    n = len(names)

    uf = _UnionFind(n)

    for i in range(n):
        for j in range(i + 1, n):
            if not _specs_compatible(specs[i], specs[j]):
                continue
            same = platforms[i] == platforms[j]
            if same:
                score = fuzz.token_sort_ratio(normalized[i], normalized[j])
                threshold = same_platform_threshold
            else:
                score = fuzz.token_set_ratio(normalized[i], normalized[j])
                threshold = cross_platform_threshold
            if score >= threshold:
                uf.union(i, j)

    # Map union-find roots to sequential cluster IDs
    root_to_id: dict[int, int] = {}
    counter = 0
    ids = []
    for i in range(n):
        root = uf.find(i)
        if root not in root_to_id:
            root_to_id[root] = counter
            counter += 1
        ids.append(root_to_id[root])

    return df.assign(producto_id=ids)


def match_across_files(
    dfs: list[pd.DataFrame],
    same_platform_threshold: int = SAME_PLATFORM_THRESHOLD,
    cross_platform_threshold: int = CROSS_PLATFORM_THRESHOLD,
) -> pd.DataFrame:
    """
    Concatenate multiple processed DataFrames (from different scrape dates) and
    assign consistent ``producto_id`` values across all of them.

    Example
    -------
    >>> from pathlib import Path
    >>> import pandas as pd
    >>> from matching import match_across_files
    >>> files = sorted(Path("data/processed").glob("*.csv"))
    >>> dfs = [pd.read_csv(f) for f in files]
    >>> combined = match_across_files(dfs)
    >>> combined.groupby("producto_id")["precio_actual_num"].plot()
    """
    combined = pd.concat(dfs, ignore_index=True)
    return build_product_id(combined, same_platform_threshold, cross_platform_threshold)


# ---------------------------------------------------------------------------
# 5. Quick smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sample = pd.DataFrame(
        {
            "nombre": [
                'Portátil Lenovo IdeaPad Slim 3 15IRH10 15,3" Intel Core i5-13420H 16GB 512GB SSD',
                'Lenovo IdeaPad Slim 3 15IRH10 15.3" i5-13420H/16GB/512GB SSD Windows 11',
                'Apple MacBook Air M2 13" 8GB 256GB SSD',
                'Apple MacBook Air (M2, 2022) 13,6" 8 GB 256 GB SSD',
                'MSI Cyborg 15 Intel Core i7 16GB 512GB RTX 4060',
            ],
            "plataforma": [
                "PcComponentes",
                "Amazon",
                "PcComponentes",
                "Amazon",
                "Amazon",
            ],
            "precio_actual_num": [599.0, 609.0, 1099.0, 1089.0, 799.0],
        }
    )

    result = build_product_id(sample)
    print(result[["nombre", "plataforma", "producto_id"]].to_string())
    print(f"\nClusters únicos: {result['producto_id'].nunique()}")
    # Expected: Lenovo pair → same id; MacBook pair → same id; MSI → own id
