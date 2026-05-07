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
        {"label": "Company Code", "fieldname": "company_code", "fieldtype": "Data", "width": 120},
        {"label": "Year", "fieldname": "fiscal_year", "fieldtype": "Data", "width": 80},
        {"label": "G/L Account No", "fieldname": "gl_account_number", "fieldtype": "Data", "width": 120},
        {"label": "G/L Account Name", "fieldname": "gl_account_name", "fieldtype": "Data", "width": 120},
        {"label": "Opening Balance (LC)", "fieldname": "opening_balance_lc", "fieldtype": "Currency", "width": 140},
        {"label": "YTD Movement (LC)", "fieldname": "ytd_movement_lc", "fieldtype": "Currency", "width": 140},
        {"label": "Ending Balance (LC)", "fieldname": "ending_balance_lc", "fieldtype": "Currency", "width": 140}
    ]

def get_data(filters):
    conditions = []
    values = {}

    if filters.get("company_code"):
        conditions.append("f.RBUKRS = %(company_code)s")
        values["company_code"] = filters["company_code"]

    if filters.get("fiscal_year"):
        conditions.append("f.RYEAR = %(fiscal_year)s")
        values["fiscal_year"] = filters["fiscal_year"]

    if filters.get("gl_number"):
        conditions.append("f.RACCT = %(gl_number)s")
        values["gl_number"] = filters["gl_number"]

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""SELECT 
        f.RBUKRS AS company_code,
        f.RYEAR AS fiscal_year,
        f.RACCT AS gl_account_number,
        k.TXT20 AS gl_account_name,
        
        -- 1. Opening Balance (Carry Forward from previous year)
        SUM(f.HSLVT) AS opening_balance_lc,
        
        -- 2. Year-to-Date Movement (Sum of Periods 1 through 12)
        SUM(f.HSL01 + f.HSL02 + f.HSL03 + f.HSL04 + f.HSL05 + f.HSL06 + 
            f.HSL07 + f.HSL08 + f.HSL09 + f.HSL10 + f.HSL11 + f.HSL12) AS ytd_movement_lc,
            
        -- 3. Ending Balance (Opening Balance + YTD Movement)
        SUM(f.HSLVT + 
            f.HSL01 + f.HSL02 + f.HSL03 + f.HSL04 + f.HSL05 + f.HSL06 + 
            f.HSL07 + f.HSL08 + f.HSL09 + f.HSL10 + f.HSL11 + f.HSL12) AS ending_balance_lc

    FROM `tabmpr-FAGLFLEXT` f

    -- Join with G/L Account Master Data for Descriptions
    LEFT JOIN `tabmpr-SKAT` k
        ON  f.RCLNT = k.MANDT
        AND f.RACCT = k.SAKNR
        AND k.SPRAS = 'E'        -- 'E' for English descriptions
        -- AND k.KTOPL = 'INT'      -- Replace 'INT' with your actual Chart of Accounts

    WHERE {where_clause}

    GROUP BY 
        f.RBUKRS,
        f.RYEAR,
        f.RACCT,
        k.TXT20

    ORDER BY 
        f.RBUKRS, 
        f.RACCT;
    """

    data = frappe.db.sql(query, values, as_dict=True)
    return data


