from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from playwright.async_api import BrowserContext, Page, async_playwright
from playwright_stealth import Stealth


RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


@dataclass
class ScrapeConfig:
    headless: bool = True
    timeout_ms: int = 45000
    wait_after_load_ms: int = 6000
    max_items_per_platform: int = 40


async def _new_context(config: ScrapeConfig) -> BrowserContext:
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=config.headless,
        args=["--disable-blink-features=AutomationControlled"],
    )
    context = await browser.new_context(
        viewport={"width": 1366, "height": 900},
        locale="es-ES",
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
    )
    await Stealth().apply_stealth_async(context)

    # Keep references on context to close everything in one place.
    context._playwright_ref = playwright  # type: ignore[attr-defined]
    context._browser_ref = browser  # type: ignore[attr-defined]
    return context


async def _close_context(context: BrowserContext) -> None:
    browser = getattr(context, "_browser_ref", None)
    playwright = getattr(context, "_playwright_ref", None)
    await context.close()
    if browser is not None:
        await browser.close()
    if playwright is not None:
        await playwright.stop()


async def _safe_text(locator) -> str | None:
    try:
        if await locator.count() == 0:
            return None
        txt = await locator.first.text_content(timeout=1500)
        if txt is None:
            return None
        clean = txt.strip()
        return clean or None
    except Exception:
        return None


def _build_price(whole: str | None, frac: str | None, fallback: str | None) -> str | None:
    if whole:
        w = whole.replace(".", "").replace("€", "").strip()
        f = (frac or "00").replace("€", "").strip()
        return f"{w}.{f}"
    if fallback:
        return fallback.replace("€", "").replace(" ", "").replace(",", ".").strip()
    return None


async def scrape_pccomponentes(config: ScrapeConfig) -> list[dict[str, Any]]:
    context = await _new_context(config)
    page = await context.new_page()
    rows: list[dict[str, Any]] = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        await page.goto(
            "https://www.pccomponentes.com/portatiles",
            wait_until="domcontentloaded",
            timeout=config.timeout_ms,
        )
        await page.wait_for_timeout(config.wait_after_load_ms)

        cards = page.locator(".product-card")
        total = min(await cards.count(), config.max_items_per_platform)
        for i in range(total):
            card = cards.nth(i)
            name = await _safe_text(card.locator("h3.product-card__title"))
            if not name:
                continue
            current_price = await _safe_text(card.locator("[data-e2e='price-card']"))
            original_price = await _safe_text(card.locator("[data-e2e='crossedPrice']"))

            rows.append(
                {
                    "nombre": name,
                    "precio_actual": current_price,
                    "precio_original": original_price,
                    "descuento": None,
                    "valoracion": None,
                    "plataforma": "PcComponentes",
                    "fecha": timestamp,
                }
            )
    finally:
        await _close_context(context)

    return rows


async def scrape_amazon(config: ScrapeConfig) -> list[dict[str, Any]]:
    context = await _new_context(config)
    page = await context.new_page()
    rows: list[dict[str, Any]] = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        await page.goto(
            "https://www.amazon.es/s?k=portatiles",
            wait_until="domcontentloaded",
            timeout=config.timeout_ms,
        )
        await page.wait_for_timeout(config.wait_after_load_ms)

        cards = page.locator("div.s-result-item[data-component-type='s-search-result']")
        total = min(await cards.count(), config.max_items_per_platform)

        for i in range(total):
            card = cards.nth(i)
            name = await _safe_text(card.locator("h2 span"))
            whole = await _safe_text(card.locator("span.a-price-whole"))
            frac = await _safe_text(card.locator("span.a-price-fraction"))
            fallback_price = await _safe_text(card.locator("span.a-price > span.a-offscreen"))
            current_price = _build_price(whole, frac, fallback_price)
            original_price = await _safe_text(card.locator("span.a-text-price span.a-offscreen"))
            rating = await _safe_text(card.locator("span.a-icon-alt"))

            if not name or not current_price:
                continue

            rows.append(
                {
                    "nombre": name.strip(),
                    "precio_actual": current_price,
                    "precio_original": original_price,
                    "descuento": None,
                    "valoracion": rating,
                    "plataforma": "Amazon",
                    "fecha": timestamp,
                }
            )
    finally:
        await _close_context(context)

    return rows


async def run_daily_scrape(max_items_per_platform: int = 40, headless: bool = True) -> pd.DataFrame:
    config = ScrapeConfig(max_items_per_platform=max_items_per_platform, headless=headless)

    try:
        pc_rows = await scrape_pccomponentes(config)
    except Exception as e:
        print(f"Error en PcComponentes: {type(e).__name__}: {e}")
        pc_rows = []

    try:
        amazon_rows = await scrape_amazon(config)
    except Exception as e:
        print(f"Error en Amazon: {type(e).__name__}: {e}")
        amazon_rows = []

    all_rows = pc_rows + amazon_rows
    df = pd.DataFrame(all_rows)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    output = RAW_DIR / f"precios_portatiles_{ts}.csv"
    df.to_csv(output, index=False)
    print(f"Archivo guardado: {output}")
    print(df["plataforma"].value_counts(dropna=False))
    return df


if __name__ == "__main__":
    result = asyncio.run(run_daily_scrape(max_items_per_platform=25, headless=True))
    print(result.head(10))
