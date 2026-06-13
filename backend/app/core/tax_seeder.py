from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from app.models.pay import TaxRule

from sqlalchemy import delete

async def seed_tax_brackets(db: AsyncSession):
    # Clear existing rules to allow re-seeding
    await db.execute(delete(TaxRule))

    rules = []

    # Spain (ES) - IRPF 2026 (Real official brackets)
    es_brackets = [
        (0, 12450, 0.19),
        (12450, 20200, 0.24),
        (20200, 35200, 0.30),
        (35200, 60000, 0.37),
        (60000, 300000, 0.45),
        (300000, None, 0.47)
    ]
    for i, (min_sal, max_sal, rate) in enumerate(es_brackets):
        rules.append(TaxRule(
            id=uuid.uuid4().hex, country_code="ES", name=f"IRPF Tramo {i+1} (2026)", 
            calculation_type="percentage", rate=rate, min_salary=min_sal, max_salary=max_sal,
            is_deduction=True, is_marginal=True
        ))
        
    # Spain (ES) - Seguridad Social (2026)
    ss_max_base = 61214.40 # 5101.20 * 12
    ss_rules = [
        ("SS Contingencias Comunes (Trabajador)", 0.0470, True),
        ("SS Desempleo (Trabajador)", 0.0155, True),
        ("SS FP (Trabajador)", 0.0010, True),
        ("SS MEI (Trabajador)", 0.0015, True),
        ("SS Contingencias Comunes (Empresa)", 0.2360, False),
        ("SS Desempleo (Empresa)", 0.0550, False),
        ("SS FP (Empresa)", 0.0060, False),
        ("SS FOGASA (Empresa)", 0.0020, False),
        ("SS MEI (Empresa)", 0.0075, False),
    ]
    for name, rate, is_deduction in ss_rules:
        rules.append(TaxRule(
            id=uuid.uuid4().hex, country_code="ES", name=name,
            calculation_type="percentage", rate=rate, min_salary=0, max_salary=ss_max_base,
            is_deduction=is_deduction, is_marginal=False
        ))

    # England/UK (UK) - 2026
    uk_brackets = [
        (0, 13500, 0.0),
        (13500, 52000, 0.20),
        (52000, 130000, 0.40),
        (130000, None, 0.45)
    ]
    for i, (min_sal, max_sal, rate) in enumerate(uk_brackets):
        rules.append(TaxRule(
            id=uuid.uuid4().hex, country_code="UK", name=f"Income Tax Band {i+1} (2026)", 
            calculation_type="percentage", rate=rate, min_salary=min_sal, max_salary=max_sal,
            is_deduction=True, is_marginal=True
        ))

    # France (FR) - 2026
    fr_brackets = [
        (0, 11500, 0.0),
        (11500, 29000, 0.11),
        (29000, 82000, 0.30),
        (82000, 175000, 0.41),
        (175000, None, 0.45)
    ]
    for i, (min_sal, max_sal, rate) in enumerate(fr_brackets):
        rules.append(TaxRule(
            id=uuid.uuid4().hex, country_code="FR", name=f"Tranche d'imposition {i+1} (2026)", 
            calculation_type="percentage", rate=rate, min_salary=min_sal, max_salary=max_sal,
            is_deduction=True, is_marginal=True
        ))

    # Germany (DE) - 2026
    de_brackets = [
        (0, 11600, 0.0),
        (11600, 65000, 0.24), 
        (65000, 285000, 0.42),
        (285000, None, 0.45)
    ]
    for i, (min_sal, max_sal, rate) in enumerate(de_brackets):
        rules.append(TaxRule(
            id=uuid.uuid4().hex, country_code="DE", name=f"Einkommensteuer {i+1} (2026)", 
            calculation_type="percentage", rate=rate, min_salary=min_sal, max_salary=max_sal,
            is_deduction=True, is_marginal=True
        ))

    # Italy (IT) - 2026
    it_brackets = [
        (0, 16000, 0.23),
        (16000, 29000, 0.25),
        (29000, 52000, 0.35),
        (52000, None, 0.43)
    ]
    for i, (min_sal, max_sal, rate) in enumerate(it_brackets):
        rules.append(TaxRule(
            id=uuid.uuid4().hex, country_code="IT", name=f"Scaglione IRPEF {i+1} (2026)", 
            calculation_type="percentage", rate=rate, min_salary=min_sal, max_salary=max_sal,
            is_deduction=True, is_marginal=True
        ))

    # Netherlands (NL) - 2026
    nl_brackets = [
        (0, 75000, 0.3693),
        (75000, None, 0.4950)
    ]
    for i, (min_sal, max_sal, rate) in enumerate(nl_brackets):
        rules.append(TaxRule(
            id=uuid.uuid4().hex, country_code="NL", name=f"Box 1 Tarief {i+1} (2026)", 
            calculation_type="percentage", rate=rate, min_salary=min_sal, max_salary=max_sal,
            is_deduction=True, is_marginal=True
        ))

    # Portugal (PT) - 2026
    pt_brackets = [
        (0, 7700, 0.145),
        (7700, 11600, 0.21),
        (11600, 16500, 0.265),
        (16500, 21500, 0.285),
        (21500, 27500, 0.35),
        (27500, 40000, 0.37),
        (40000, 52500, 0.435),
        (52500, 81000, 0.45),
        (81000, None, 0.48)
    ]
    for i, (min_sal, max_sal, rate) in enumerate(pt_brackets):
        rules.append(TaxRule(
            id=uuid.uuid4().hex, country_code="PT", name=f"Escalão IRS {i+1} (2026)", 
            calculation_type="percentage", rate=rate, min_salary=min_sal, max_salary=max_sal,
            is_deduction=True, is_marginal=True
        ))

    db.add_all(rules)
    await db.commit()
    return {"message": f"Successfully seeded {len(rules)} tax brackets for ES, UK, FR, DE, IT, NL, PT."}
