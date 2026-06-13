import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger("successcore.sepa")


def generate_sepa_xml(
    payments: List[Dict[str, Any]],
    company: Dict[str, Any],
    execution_date: Optional[str] = None,
    batch_booking: bool = True,
) -> str:
    message_id = f"SAS-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    creation_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    exec_date = execution_date or datetime.now().strftime("%Y-%m-%d")
    total_amount = sum(p.get("amount", 0) for p in payments)
    ctrl_sum = round(total_amount, 2)

    head = f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <CstmrCdtTrfInitn>
    <GrpHdr>
      <MsgId>{message_id}</MsgId>
      <CreDtTm>{creation_time}</CreDtTm>
      <NbOfTxs>{len(payments)}</NbOfTxs>
      <CtrlSum>{ctrl_sum:.2f}</CtrlSum>
      <InitgPty>
        <Nm>{company.get('name', 'SuccessCore HR')}</Nm>
        <Id><OrgId><Othr><Id>{company.get('tax_id', '')}</Id></Othr></OrgId></Id>
      </InitgPty>
    </GrpHdr>
    <PmtInf>
      <PmtInfId>{message_id}-01</PmtInfId>
      <PmtMtd>TRF</PmtMtd>
      <BtchBookg>{'true' if batch_booking else 'false'}</BtchBookg>
      <NbOfTxs>{len(payments)}</NbOfTxs>
      <CtrlSum>{ctrl_sum:.2f}</CtrlSum>
      <PmtTpInf>
        <SvcLvl><Cd>SEPA</Cd></SvcLvl>
      </PmtTpInf>
      <ReqdExctnDt>{exec_date}</ReqdExctnDt>
      <Dbtr>
        <Nm>{company.get('name', 'SuccessCore HR')}</Nm>
        <PstlAdr>
          <Ctry>{company.get('country', 'ES')}</Ctry>
          <AdrLine>{company.get('address', '')}</AdrLine>
        </PstlAdr>
      </Dbtr>
      <DbtrAcct>
        <Id><IBAN>{company.get('iban', '')}</IBAN></Id>
        <Ccy>{payments[0].get('currency', 'EUR') if payments else 'EUR'}</Ccy>
      </DbtrAcct>
      <DbtrAgt>
        <FinInstnId><BIC>{company.get('bic', '')}</BIC></FinInstnId>
      </DbtrAgt>"""

    transactions = []
    for idx, p in enumerate(payments):
        end_to_end = f"PAY-{datetime.now().strftime('%Y%m%d')}-{idx+1:04d}"
        tx = f"""
      <CdtTrfTxInf>
        <PmtId>
          <EndToEndId>{end_to_end}</EndToEndId>
        </PmtId>
        <Amt>
          <InstdAmt Ccy="{p.get('currency', 'EUR')}">{p.get('amount', 0):.2f}</InstdAmt>
        </Amt>
        <CdtrAgt>
          <FinInstnId><BIC>{p.get('bic', '')}</BIC></FinInstnId>
        </CdtrAgt>
        <Cdtr>
          <Nm>{p.get('name', '')}</Nm>
          <PstlAdr>
            <Ctry>{p.get('country', 'ES')}</Ctry>
          </PstlAdr>
        </Cdtr>
        <CdtrAcct>
          <Id><IBAN>{p.get('iban', '')}</IBAN></Id>
        </CdtrAcct>
        <RmtInf>
          <Ustrd>{p.get('reference', f'Salary {datetime.now().strftime("%B %Y")}')}</Ustrd>
        </RmtInf>
      </CdtTrfTxInf>"""
        transactions.append(tx)

    transactions_xml = "".join(transactions)

    tail = """    </PmtInf>
  </CstmrCdtTrfInitn>
</Document>"""

    return head + transactions_xml + tail


def generate_salary_sepa_xml(
    employees_net_pay: List[Dict[str, Any]],
    company: Dict[str, Any],
    execution_date: Optional[str] = None,
) -> str:
    payments = []
    for emp in employees_net_pay:
        payments.append({
            "name": emp.get("full_name", ""),
            "iban": emp.get("iban", ""),
            "bic": emp.get("bic", ""),
            "amount": emp.get("net_pay", 0),
            "currency": emp.get("currency", "EUR"),
            "reference": f"Nomina {emp.get('period', '')} - {emp.get('full_name', '')}",
            "country": emp.get("country", "ES"),
        })

    return generate_sepa_xml(payments, company, execution_date)
