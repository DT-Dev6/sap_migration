# Copyright (c) 2026, Digitalis Technologies Pvt Ltd and contributors
# For license information, please see license.txt

from frappe.utils import getdate

import frappe

def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": "Item Status", "fieldname": "item_status", "fieldtype": "Data", "width": 120},
        {"label": "Company Code", "fieldname": "company_code", "fieldtype": "Data", "width": 120},
        {"label": "G/L No", "fieldname": "gl_number", "fieldtype": "Data", "width": 140},
        {"label": "G/L Account", "fieldname": "gl_account", "fieldtype": "Data", "width": 140},
        {"label": "Document No", "fieldname": "document_no", "fieldtype": "Data", "width": 140},
        {"label": "Year", "fieldname": "fiscal_year", "fieldtype": "Data", "width": 80},
        {"label": "Month", "fieldname": "fiscal_month", "fieldtype": "Data", "width": 80},
        {"label": "Line Item", "fieldname": "line_item", "fieldtype": "Data", "width": 80},
        {"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": "Document Date", "fieldname": "document_date", "fieldtype": "Date", "width": 100},
        {"label": "Document Type", "fieldname": "document_type", "fieldtype": "Data", "width": 100},
        {"label": "Posting Key", "fieldname": "posting_key", "fieldtype": "Data", "width": 100},
        {"label": "Business Place", "fieldname": "business_place", "fieldtype": "Data", "width": 120},
        {"label": "Profit Center", "fieldname": "profit_center", "fieldtype": "Data", "width": 120},
        {"label": "Document Header Text", "fieldname": "document_header_text", "fieldtype": "Data", "width": 150},
        {"label": "Assignment", "fieldname": "assignment", "fieldtype": "Data", "width": 80},
        {"label": "Item Text", "fieldname": "item_text", "fieldtype": "Data", "width": 120},
        {"label": "Debit/Credit Ind", "fieldname": "debit_credit_ind", "fieldtype": "Data", "width": 120},
        {"label": "Amount (Local Currency)", "fieldname": "amount_local_currency", "fieldtype": "Currency", "width": 120},
        {"label": "Amount (Document Currency)", "fieldname": "amount_doc_currency", "fieldtype": "Currency", "width": 120},
        {"label": "Balance", "fieldname": "balance", "fieldtype": "Currency", "width": 120},
        {"label": "Currency", "fieldname": "currency", "fieldtype": "Data", "width": 200},
        {"label": "Clearing Document", "fieldname": "clearing_document", "fieldtype": "Data", "width": 120},
        {"label": "Clearing Date", "fieldname": "clearing_date", "fieldtype": "Date", "width": 100},
        {"label": "Entered By", "fieldname": "entered_by", "fieldtype": "Data", "width": 120}
    ]

def get_data(filters):
    conditions = []
    values = {}

    # if filters.get("company_code"):
    #     conditions.append("bseg.bukrs = %(company_code)s")
    #     values["company_code"] = filters["company_code"]

    # if filters.get("gl_account"):
    #     conditions.append("bseg.hkont = %(gl_account)s")
    #     values["gl_account"] = filters["gl_account"]

    # if filters.get("from_date"):
    #     conditions.append("bkpf.budat >= %(from_date)s")
    #     values["from_date"] = filters["from_date"]

    # if filters.get("to_date"):
    #     conditions.append("bkpf.budat <= %(to_date)s")
    #     values["to_date"] = filters["to_date"]

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    company_code = filters.get("company_code")
    gl_number = filters.get("gl_number")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    query = f"""WITH GL_Line_Items AS (
        SELECT 
            MANDT,
            BUKRS,
            HKONT,
            AUGDT,
            AUGBL,
            ZUONR,
            GJAHR,
            BELNR,
            BUZEI,
            BUDAT,
            BLDAT,
            WAERS,
            BLART,
            SHKZG,
            DMBTR,
            WRBTR,
            SGTXT,
            MONAT,
            BSCHL,
            BUPLA,
            PRCTR,
            'Open' AS Item_Status
        FROM `tabmpr-BSIS`
            Where BUKRS = '{company_code}'
            and STR_TO_DATE(budat, '%Y%m%d') >= '{from_date}'
            and HKONT = '{gl_number}'
            and STR_TO_DATE(budat, '%Y%m%d') <= '{to_date}'


        UNION ALL

        SELECT 
            MANDT,
            BUKRS,
            HKONT,
            AUGDT,
            AUGBL,
            ZUONR,
            GJAHR,
            BELNR,
            BUZEI,
            BUDAT,
            BLDAT,
            WAERS,
            BLART,
            SHKZG,
            DMBTR,
            WRBTR,
            SGTXT,
            MONAT,
            BSCHL,
            BUPLA,
            PRCTR,
            'Cleared' AS Item_Status
        FROM `tabmpr-BSAS`
            Where BUKRS = '{company_code}'
            and HKONT = '{gl_number}'
            and STR_TO_DATE(budat, '%Y%m%d') >= '{from_date}'
            and STR_TO_DATE(budat, '%Y%m%d') <= '{to_date}'
    )

    SELECT
        i.Item_Status as item_status,
        i.BUKRS AS company_code,
        i.HKONT AS gl_number,
        t.TXT20 AS gl_account,
        i.BELNR AS document_no,
        i.GJAHR AS fiscal_year,
        i.MONAT AS fiscal_month,
        i.BUZEI AS line_item,
        i.BLART AS document_type,
        i.BUDAT AS posting_date,
        i.BLDAT AS document_date,
        i.BSCHL AS posting_key,
        i.BUPLA AS business_place,
        i.PRCTR AS profit_center,
        h.BKTXT AS document_header_text,
        i.ZUONR AS assignment,
        i.SGTXT AS item_text,
        i.SHKZG AS debit_credit_ind,

        CASE
            WHEN i.SHKZG = 'H' THEN i.DMBTR * -1
            ELSE i.DMBTR
        END AS amount_local_currency,

        CASE
            WHEN i.SHKZG = 'H' THEN i.WRBTR * -1
            ELSE i.WRBTR
        END AS amount_doc_currency,

        i.WAERS AS currency,
        i.AUGBL AS clearing_document,
        i.AUGDT AS clearing_date,
        h.USNAM AS entered_by

    FROM GL_Line_Items i

    INNER JOIN `tabmpr-BKPF` h
        ON i.MANDT = h.MANDT
        AND i.BUKRS = h.BUKRS
        AND i.BELNR = h.BELNR
        AND i.GJAHR = h.GJAHR

    LEFT JOIN `tabmpr-SKAT` t
        ON i.MANDT = t.MANDT
        AND i.HKONT = t.SAKNR
        AND t.SPRAS = 'E'
        -- AND t.KTOPL = 'INT'

    ORDER BY
        i.BUKRS,
        i.HKONT,
        i.BUDAT,
        i.BELNR;
    """
    frappe.errprint(query)

    data = frappe.db.sql(query, as_dict=True)
    # frappe.errprint(data[0].get("BUDAT"))
    # frappe.errprint(type(data[0].get("BUDAT")))
    # data_date = getdate(data[0].get("BUDAT"))
    # frappe.errprint(data_date)
    # frappe.errprint(type(data_date))
    balance = 0
    for i in data:
        balance += i.get("amount_local_currency", 0)
        i["balance"] = balance
    return data


