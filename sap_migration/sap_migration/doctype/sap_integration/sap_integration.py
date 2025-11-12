# Copyright (c) 2025, Digitalis Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import base64
import frappe
from frappe.model.document import Document
from sap_migration.sap_integration.mssql_connect import MSSQL

MSSQL_TO_FRAPPE_TYPES = {
    "bit": "Check",
    "tinyint": "Int",
    "smallint": "Int",
    "int": "Int",
    "bigint": "Int",
    "decimal": "Float",
    "numeric": "Float",
    "money": "Currency",
    "smallmoney": "Currency",
    "float": "Float",
    "real": "Float",
    "char": "Data",
    "varchar": "Data",
    "nvarchar": "Data",
    "varchar(max)": "Small Text",
    "nvarchar(max)": "Small Text",
    "text": "Text Editor",
    "ntext": "Text Editor",
    "binary": "Attach",
    "varbinary": "Attach",
    "varbinary(max)": "Attach",
    "image": "Attach",
    "uniqueidentifier": "Data",
    "date": "Data",
    "time": "Data",
    "datetime": "Data",
    "datetime2": "Data",
    "smalldatetime": "Data",
    "datetimeoffset": "Data",
    "xml": "Code",
    "rowversion": "Data",
    "sql_variant": "Data",
    "geometry": "Data",
    "geography": "Data",
}


class SAPIntegration(Document):
	@frappe.whitelist()
	def migrate_database(self):
		frappe.enqueue(
			mssql_table_migration,   # 👈 function reference, not string
			queue="long",
			timeout=600000
		)

def mssql_table_migration():
	db = MSSQL()
	database_tables = db.run("""SELECT *
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE='BASE TABLE' """)
	
	for table in database_tables:
		table_name = table.get("TABLE_NAME")
		doctype_name = f'{table.get("TABLE_SCHEMA")}-{table.get("TABLE_NAME")}'.replace("-/", "-").replace("/", "-")
		if frappe.db.exists("DocType", doctype_name):
			continue
		columns = db.run("""SELECT COLUMN_NAME, DATA_TYPE 
			FROM INFORMATION_SCHEMA.COLUMNS 
			WHERE TABLE_NAME = '{0}';
		""".format(table_name))
		if not frappe.db.exists("Database Table Migration Log", doctype_name):
			log = frappe.new_doc("Database Table Migration Log")
			log.table_name = table_name
			log.doctype_name = doctype_name
			log.insert(ignore_permissions=True)
			frappe.db.commit()
		frappe.enqueue(
			create_doctype,
			doctype_name=doctype_name,
			columns= columns,
			table_name= table_name,
			queue="long",
			timeout=600000
		)
		
		

def create_doctype(doctype_name: str, columns: list, table_name: str):
	doctype = frappe.new_doc("DocType")
	doctype.name = doctype_name
	doctype.module = "Database Table"
	doctype.custom = 1

	doctype_fields = []
	for col in columns:
		doctype_fields.append({
			"label": col.get('COLUMN_NAME'),
			"fieldtype": convert_mssql_to_frappe(col.get('DATA_TYPE'))
		})
	doctype.set("fields", doctype_fields)
	doctype.set("permissions", [{
		"role": "System Manager",
		"permlevel": 0,
		"if_owner": 0,
		"read": 1,
		"write": 1,
		"create": 1,
		"delete": 1,
		"submit": 0,
		"cancel": 0,
		"amend": 0,
		"report": 1,
		"import": 0,
		"export": 1,
		"share": 1,
		"print": 1,
		"email": 1,
	}])
	doctype.insert(ignore_permissions=True)

	log = frappe.get_doc("Database Table Migration Log", doctype_name)
	log.table_created = 1
	log.save()

	frappe.db.commit()
	frappe.enqueue(
		mssql_table_data_migration,
		doctype=doctype_name,
		table_name= table_name,
		queue="long",
		timeout=600000
	)
	


def convert_mssql_to_frappe(dtype: str) -> str:
    dtype = dtype.lower().strip()
    return MSSQL_TO_FRAPPE_TYPES.get(dtype, "Data")  # Default fallback


def mssql_table_data_migration(doctype, table_name):
	restricted = (
		"name",
		"parent",
		"creation",
		"owner",
		"modified",
		"modified_by",
		"parentfield",
		"parenttype",
		"file_list",
		"flags",
		"docstatus",
	)
	# if not db:
	db = MSSQL()
	records = db.run("""SELECT * FROM mpr.[{0}]""".format(table_name))
	# frappe.log_error(str(records), "Sap migration data table")
	for record in records:
		file_dict = []
		doc = frappe.new_doc(doctype)
		for key, value in record.items():
			key = key.strip().lower().replace(" ", "_").strip("?")
			if key in restricted:
				key = key + "1"
			if isinstance(value, (bytes, bytearray)):
				file_dict.append({key: value})
			else:
				doc.set(key, value)
		doc.insert(ignore_mandatory=True)
		frappe.db.commit()
		for file in file_dict:
			for key, value in file.items():
				# frappe.error_log(str(value), "File Value")
				# print(value)
				encoded_data = base64.b64encode(value)
				# frappe.error_log(str(encoded_data), "Encoded File Value")
				# print(encoded_data)
				# Create file in Frappe
				file_doc = frappe.get_doc({
					"doctype": "File",
					"file_name": key,
					"attached_to_doctype": doc.doctype,
					"attached_to_name": doc.name,
					"attached_to_field": key,
					"content": encoded_data,     # base64 string
					"decode": True,              # auto-decodes base64
					"is_private": 1,
					"folder": "Home/Attachments"
				})
				file_doc.insert(ignore_permissions=True)
				doc.set(key, file_doc.file_url)
			doc.save()
			frappe.db.commit()
	log = frappe.get_doc("Database Table Migration Log", doctype)
	log.data_migrated = 1
	log.save()

