import logging
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("successcore.siltra_sepe")


SEPE_CATEGORY_KEYS = {
    "100": "Contratos indefinidos - Tiempo completo",
    "200": "Contratos indefinidos - Tiempo parcial",
    "300": "Contratos temporales - Tiempo completo",
    "400": "Contratos temporales - Tiempo parcial",
    "410": "Contratos formativos",
    "420": "Contratos de prácticas",
}

CONTRACT_TYPE_TO_SEPE = {
    "indefinido": "100",
    "indefinido_tiempo_parcial": "200",
    "temporal": "300",
    "temporal_parcial": "400",
    "formacion": "410",
    "practicas": "420",
}


def generate_siltra_afiliacion_xml(
    company: Dict[str, Any],
    employees: List[Dict[str, Any]],
    period: str = "",
) -> str:
    now = datetime.now(timezone.utc)
    company_ccc = company.get("ccc", "")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<AFILIACION xmlns="http://www.seg-social.es/siltra/afiliacion">
  <Cabecera>
    <CodigoCuenta>{company_ccc}</CodigoCuenta>
    <FechaGeneracion>{now.strftime('%Y-%m-%d')}</FechaGeneracion>
    <HoraGeneracion>{now.strftime('%H:%M:%S')}</HoraGeneracion>
    <Periodo>{period or now.strftime('%Y%m')}</Periodo>
    <Empresa>
      <Nombre>{company.get('name', '')}</Nombre>
      <CIF>{company.get('tax_id', '')}</CIF>
      <CodigoCuentaCotizacion>{company_ccc}</CodigoCuentaCotizacion>
    </Empresa>
  </Cabecera>
  <Trabajadores>"""

    for emp in employees:
        xml += f"""
    <Trabajador>
      <NAF>{emp.get('ss_number', '')}</NAF>
      <Nombre>{emp.get('full_name', '')}</Nombre>
      <Apellido1>{emp.get('last_name1', '')}</Apellido1>
      <Apellido2>{emp.get('last_name2', '')}</Apellido2>
      <FechaNacimiento>{emp.get('birth_date', '')}</FechaNacimiento>
      <NIF>{emp.get('tax_id', '')}</NIF>
      <FechaAlta>{emp.get('hire_date', '')}</FechaAlta>
      <FechaBaja>{emp.get('termination_date', '')}</FechaBaja>
      <TipoContrato>{emp.get('contract_type_code', '100')}</TipoContrato>
      <CoeficienteTiempoParcial>{emp.get('part_time_pct', '100')}</CoeficienteTiempoParcial>
      <GrupoCotizacion>{emp.get('contribution_group', '1')}</GrupoCotizacion>
      <EpigrafeAT>{emp.get('at_code', '')}</EpigrafeAT>
      <Ocupacion>{emp.get('occupation_code', '')}</Ocupacion>
    </Trabajador>"""

    xml += """
  </Trabajadores>
</AFILIACION>"""
    return xml


def generate_siltra_cotizacion_xml(
    company: Dict[str, Any],
    employees_payroll: List[Dict[str, Any]],
    period: str = "",
) -> str:
    now = datetime.now(timezone.utc)
    company_ccc = company.get("ccc", "")

    total_employees = len(employees_payroll)
    total_remuneration = sum(e.get("gross_salary", 0) for e in employees_payroll)
    total_employer_cost = sum(e.get("employer_cost", 0) for e in employees_payroll)

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<COTIZACION xmlns="http://www.seg-social.es/siltra/cotizacion">
  <Cabecera>
    <CodigoCuenta>{company_ccc}</CodigoCuenta>
    <FechaGeneracion>{now.strftime('%Y-%m-%d')}</FechaGeneracion>
    <Periodo>{period or now.strftime('%Y%m')}</Periodo>
  </Cabecera>
  <ResumenEmpresa>
    <TotalTrabajadores>{total_employees}</TotalTrabajadores>
    <ImporteRemuneracion>{total_remuneration:.2f}</ImporteRemuneracion>
    <ImporteCotizacionEmpresa>{total_employer_cost:.2f}</ImporteCotizacionEmpresa>
  </ResumenEmpresa>
  <Trabajadores>"""

    for emp in employees_payroll:
        xml += f"""
    <Trabajador>
      <NAF>{emp.get('ss_number', '')}</NAF>
      <Nombre>{emp.get('full_name', '')}</Nombre>
      <Remuneracion>{emp.get('gross_salary', 0):.2f}</Remuneracion>
      <BaseContingenciasComunes>{emp.get('cc_base', 0):.2f}</BaseContingenciasComunes>
      <BaseContingenciasProfesionales>{emp.get('cp_base', 0):.2f}</BaseContingenciasProfesionales>
      <BaseDesempleo>{emp.get('unemp_base', 0):.2f}</BaseDesempleo>
      <BaseFOGASA>{emp.get('fogasa_base', 0):.2f}</BaseFOGASA>
      <BaseFormacionProfesional>{emp.get('fp_base', 0):.2f}</BaseFormacionProfesional>
      <CuotaEmpresa>{emp.get('employer_cost', 0):.2f}</CuotaEmpresa>
      <CuotaTrabajador>{emp.get('employee_cost', 0):.2f}</CuotaTrabajador>
      <HorasExtras>{emp.get('overtime_hours', 0):.1f}</HorasExtras>
      <DiasCotizados>{emp.get('days_worked', 30)}</DiasCotizados>
    </Trabajador>"""

    xml += """
  </Trabajadores>
</COTIZACION>"""
    return xml


def generate_sepe_contrato_comunicacion(
    company: Dict[str, Any],
    employee: Dict[str, Any],
    contract_type: str = "indefinido",
) -> str:
    now = datetime.now(timezone.utc)
    sepe_code = CONTRACT_TYPE_TO_SEPE.get(contract_type, "100")
    employee_id = uuid.uuid4().hex[:12]

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<CONTRATOS xmlns="http://www.sepe.es/comunicacion">
  <Cabecera>
    <IdComunicacion>{employee_id}</IdComunicacion>
    <FechaComunicacion>{now.strftime('%Y-%m-%d')}</FechaComunicacion>
    <HoraComunicacion>{now.strftime('%H:%M:%S')}</HoraComunicacion>
    <TipoComunicacion>ALTA</TipoComunicacion>
  </Cabecera>
  <Empresa>
    <CIF>{company.get('tax_id', '')}</CIF>
    <Nombre>{company.get('name', '')}</Nombre>
    <CodigoCuenta>{company.get('ccc', '')}</CodigoCuenta>
  </Empresa>
  <Trabajador>
    <NIF>{employee.get('tax_id', '')}</NIF>
    <NAF>{employee.get('ss_number', '')}</NAF>
    <Nombre>{employee.get('full_name', '')}</Nombre>
    <FechaNacimiento>{employee.get('birth_date', '')}</FechaNacimiento>
    <Nacionalidad>{employee.get('nationality', 'ES')}</Nacionalidad>
    <NivelFormativo>{employee.get('education_level', '')}</NivelFormativo>
  </Trabajador>
  <Contrato>
    <FechaInicio>{employee.get('hire_date', '')}</FechaInicio>
    <FechaFin>{employee.get('contract_end_date', '')}</FechaFin>
    <CodigoContrato>{sepe_code}</CodigoContrato>
    <Jornada>{employee.get('workday_type_code', 'COMPLETA')}</Jornada>
    <DuracionJornada>{employee.get('weekly_hours', '40')}</DuracionJornada>
    <SalarioBase>{employee.get('base_salary', 0):.2f}</SalarioBase>
    <PeriodoSalarial>MENSUAL</PeriodoSalarial>
    <Ocupacion>{employee.get('occupation_code', '')}</Ocupacion>
    <ConvenioColectivo>{employee.get('collective_agreement', '')}</ConvenioColectivo>
  </Contrato>
  <CentroTrabajo>
    <Direccion>{company.get('address', '')}</Direccion>
    <Municipio>{company.get('city', '')}</Municipio>
    <CodigoPostal>{company.get('postal_code', '')}</CodigoPostal>
    <Provincia>{company.get('province', '')}</Provincia>
  </CentroTrabajo>
</CONTRATOS>"""
    return xml


async def calculate_social_security_costs(
    gross_salary: float,
    contribution_group: str = "1",
    contract_type: str = "indefinido",
) -> Dict[str, float]:
    CC_EMPLOYER_BASE = 23.60
    CC_EMPLOYEE_BASE = 4.70
    CP_EMPLOYER = 1.50
    UNEMP_EMPLOYER_INDEF = 5.50
    UNEMP_EMPLOYER_TEMP = 6.70
    UNEMP_EMPLOYEE_INDEF = 1.55
    UNEMP_EMPLOYEE_TEMP = 1.60
    FOGASA_EMPLOYER = 0.20
    FP_EMPLOYER = 0.60
    FP_EMPLOYEE = 0.10

    if "parcial" in contract_type:
        gross_salary = gross_salary * 0.5

    unemp_employer = UNEMP_EMPLOYER_TEMP if "temporal" in contract_type else UNEMP_EMPLOYER_INDEF
    unemp_employee = UNEMP_EMPLOYEE_TEMP if "temporal" in contract_type else UNEMP_EMPLOYEE_INDEF

    cc_employer = gross_salary * CC_EMPLOYER_BASE / 100
    cc_employee = gross_salary * CC_EMPLOYEE_BASE / 100
    cp_employer = gross_salary * CP_EMPLOYER / 100
    unemp_employer_cost = gross_salary * unemp_employer / 100
    unemp_employee_cost = gross_salary * unemp_employee / 100
    fogasa = gross_salary * FOGASA_EMPLOYER / 100
    fp_employer = gross_salary * FP_EMPLOYER / 100
    fp_employee = gross_salary * FP_EMPLOYEE / 100

    total_employer = cc_employer + cp_employer + unemp_employer_cost + fogasa + fp_employer
    total_employee = cc_employee + unemp_employee_cost + fp_employee

    return {
        "gross_salary": round(gross_salary, 2),
        "cc_employer": round(cc_employer, 2),
        "cc_employee": round(cc_employee, 2),
        "cp_employer": round(cp_employer, 2),
        "unemp_employer": round(unemp_employer_cost, 2),
        "unemp_employee": round(unemp_employee_cost, 2),
        "fogasa_employer": round(fogasa, 2),
        "fp_employer": round(fp_employer, 2),
        "fp_employee": round(fp_employee, 2),
        "total_employer_cost": round(total_employer, 2),
        "total_employee_cost": round(total_employee, 2),
        "net_employee": round(gross_salary - total_employee, 2),
    }
