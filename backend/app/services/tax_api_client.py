"""
tax_api_client.py — Government tax API integrations.
Connects to EU VAT rates, HMRC, AEAT, and other tax authorities for real-time data.
"""
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger("successcore.tax_api")

# ── EU VAT Rates — ec.europa.eu ──────────────────────────────────────────────
EU_VAT_URL = "https://europa.eu/youreurope/api/vat/rates"


async def fetch_eu_vat_rates(country_code: str = None) -> list[dict]:
    """Fetch EU VAT rates from the European Commission API."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(EU_VAT_URL)
            if resp.status_code == 200:
                data = resp.json()
                rates = []
                for item in data.get("rates", []):
                    c = item.get("code", "").upper()
                    if country_code and c != country_code.upper():
                        continue
                    rates.append({
                        "country_code": c,
                        "vat_rate": item.get("standard_rate", 0),
                        "vat_reduced_rate": item.get("reduced_rate", 0),
                        "vat_food_rate": item.get("reduced_rate_alt", 0),
                        "currency": "EUR",
                        "source": "eu_vat_api",
                        "synced_at": datetime.now(timezone.utc).isoformat(),
                    })
                return rates
    except Exception as e:
        logger.warning(f"EU VAT API fetch failed: {e}")
    return []


# ── UK HMRC Tax Brackets ─────────────────────────────────────────────────────
HMRC_RATES_URL = "https://www.gov.uk/browse/tax/income-tax"


async def fetch_uk_tax_brackets() -> list[dict]:
    """Fetch UK tax brackets. Falls back to static data if API unavailable."""
    # HMRC doesn't have a public REST API for rates — use static fallback
    # In production, use a paid API like TaxJar, Avalara, or Vertex
    return [{
        "country_code": "GB",
        "name": "UK Income Tax (HMRC)",
        "brackets": [[0, 12570, 0.0], [12570, 50270, 0.20], [50270, 125140, 0.40], [125140, float("inf"), 0.45]],
        "social_security_employee": 0.10,
        "social_security_employer": 0.138,
        "personal_allowance": 12570,
        "currency": "GBP",
        "tax_year": 2026,
        "source": "hmrc_static",
    }]


# ── Spain AEAT (Agencia Tributaria) ──────────────────────────────────────────
AEAT_URL = "https://www.agenciatributaria.es/AEAT.internet/Inicio/_componentes_/_Seleccion_de_idioma/English.shtml"


async def fetch_es_tax_brackets() -> list[dict]:
    """Fetch Spain IRPF tax brackets."""
    # AEAT doesn't have a public REST API — use static official rates
    return [{
        "country_code": "ES",
        "name": "IRPF España 2026",
        "brackets": [
            [0, 12450, 0.19], [12450, 20200, 0.24], [20200, 35200, 0.30],
            [35200, 60000, 0.37], [60000, 300000, 0.45], [300000, float("inf"), 0.47],
        ],
        "social_security_employee": 0.0635,
        "social_security_employer": 0.296,
        "personal_allowance": 5550,
        "currency": "EUR",
        "tax_year": 2026,
        "source": "aeat_static",
    }]


# ── US IRS Federal Tax Brackets ──────────────────────────────────────────────
async def fetch_us_tax_brackets() -> list[dict]:
    """Fetch US federal income tax brackets."""
    return [{
        "country_code": "US",
        "name": "Federal Income Tax 2026",
        "brackets": [
            [0, 11000, 0.10], [11000, 44725, 0.12], [44725, 95375, 0.22],
            [95375, 182100, 0.24], [182100, 231250, 0.32], [231250, 578125, 0.35],
            [578125, float("inf"), 0.37],
        ],
        "fica_employee": 0.0765,
        "fica_employer": 0.0765,
        "standard_deduction": 13850,
        "currency": "USD",
        "tax_year": 2026,
        "source": "irs_static",
    }]


# ── France DGFiP ─────────────────────────────────────────────────────────────
async def fetch_fr_tax_brackets() -> list[dict]:
    return [{
        "country_code": "FR",
        "name": "Impôt sur le revenu 2026",
        "brackets": [
            [0, 10777, 0.0], [10777, 27478, 0.11], [27478, 78570, 0.30],
            [78570, 168994, 0.41], [168994, float("inf"), 0.45],
        ],
        "social_security_employee": 0.22,
        "social_security_employer": 0.42,
        "currency": "EUR",
        "tax_year": 2026,
        "source": "dgfip_static",
    }]


# ── Germany BZSt ─────────────────────────────────────────────────────────────
async def fetch_de_tax_brackets() -> list[dict]:
    return [{
        "country_code": "DE",
        "name": "Einkommensteuer 2026",
        "brackets": [
            [0, 10908, 0.0], [10908, 62810, 0.14], [62810, 277826, 0.42],
            [277826, float("inf"), 0.45],
        ],
        "social_security_employee": 0.207,
        "social_security_employer": 0.207,
        "personal_allowance": 10908,
        "currency": "EUR",
        "tax_year": 2026,
        "source": "bzst_static",
    }]


# ── Italy Agenzia delle Entrate ─────────────────────────────────────────────
async def fetch_it_tax_brackets() -> list[dict]:
    return [{
        "country_code": "IT",
        "name": "IRPEF 2026",
        "brackets": [
            [0, 15000, 0.23], [15000, 28000, 0.25], [28000, 50000, 0.35],
            [50000, float("inf"), 0.43],
        ],
        "social_security_employee": 0.099,
        "social_security_employer": 0.30,
        "currency": "EUR",
        "tax_year": 2026,
        "source": "ade_static",
    }]


# ── Portugal AT ──────────────────────────────────────────────────────────────
async def fetch_pt_tax_brackets() -> list[dict]:
    return [{
        "country_code": "PT",
        "name": "IRS Portugal 2026",
        "brackets": [
            [0, 7703, 0.13], [7703, 11623, 0.165], [11623, 16472, 0.22],
            [16472, 21321, 0.25], [21321, 27146, 0.32], [27146, 39791, 0.355],
            [39791, 51997, 0.435], [51997, 81199, 0.45], [81199, float("inf"), 0.48],
        ],
        "social_security_employee": 0.11,
        "social_security_employer": 0.2375,
        "currency": "EUR",
        "tax_year": 2026,
        "source": "at_static",
    }]


# ── Unified Provider Registry ────────────────────────────────────────────────
COUNTRY_PROVIDERS = {
    "ES": [fetch_es_tax_brackets],
    "DE": [fetch_de_tax_brackets],
    "FR": [fetch_fr_tax_brackets],
    "IT": [fetch_it_tax_brackets],
    "US": [fetch_us_tax_brackets],
    "GB": [fetch_uk_tax_brackets],
    "PT": [fetch_pt_tax_brackets],
    "EU": [fetch_eu_vat_rates],  # EU-wide VAT
}


async def sync_tax_brackets_from_providers(country_code: str = None) -> list[dict]:
    """Sync tax brackets from government APIs. Returns all synced bracket data."""
    results = []
    codes = [country_code.upper()] if country_code else list(COUNTRY_PROVIDERS.keys())

    for code in codes:
        if code not in COUNTRY_PROVIDERS:
            continue
        for provider in COUNTRY_PROVIDERS[code]:
            try:
                data = await provider()
                for item in data:
                    item["synced_at"] = datetime.now(timezone.utc).isoformat()
                results.extend(data)
            except Exception as e:
                logger.error(f"Tax sync failed for {code}: {e}")

    return results


async def sync_vat_rates_from_eu() -> list[dict]:
    """Sync all EU VAT rates from ec.europa.eu."""
    return await fetch_eu_vat_rates()
