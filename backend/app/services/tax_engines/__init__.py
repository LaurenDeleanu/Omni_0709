from .base import BaseTaxEngine, TaxCalculationResult
from .es_irpf import ESTaxEngine
from .uk_paye import UKTaxEngine
from .pt_irs import PTTaxEngine
from .de_lohnsteuer import DETaxEngine
from .generic import GenericTaxEngine

_engines = {
    "ES": ESTaxEngine(),
    "UK": UKTaxEngine(),
    "GB": UKTaxEngine(),
    "PT": PTTaxEngine(),
    "DE": DETaxEngine(),
}

def get_tax_engine(country_code: str) -> BaseTaxEngine:
    """Returns the tax engine for a given country code, or a generic fallback."""
    return _engines.get(country_code.upper(), GenericTaxEngine())
