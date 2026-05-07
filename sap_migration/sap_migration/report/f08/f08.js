// Copyright (c) 2026, Digitalis Technologies Pvt Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["F08"] = {
    "filters": [
        {
            fieldname: "company_code",
            label: "Company Code",
            fieldtype: "Data",
            default: '1000',
            reqd: 1
        },
        {
            fieldname: "fiscal_year",
            label: "Fiscal Year",
            fieldtype: "Data"
        },
		{
			fieldname: "gl_number",
			label: "GL Number",
			fieldtype: "Data"
		}
    ]
};
