# Copyright (c) 2025, Digitalis Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import base64
import frappe
from frappe.model.document import Document
from sap_migration.sap_integration.mssql_connect import MSSQL
from frappe.utils import cint, now
from frappe.model.naming import make_autoname

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


class SAPIntegration(Document):
    @frappe.whitelist()
    def migrate_database(self):
        frappe.enqueue(
            mssql_table_migration,   # 👈 function reference, not string
            queue="long",
            timeout=600000
        )

    @frappe.whitelist()
    def migrate_error_tables(self):
        frappe.enqueue(
            msql_error_table_migration,   # 👈 function reference, not string
            queue="long",
            timeout=600000
        )

    @frappe.whitelist()
    def migrate_error_data_tables(self):
        frappe.enqueue(
            msql_error_data_table_migration,   # 👈 function reference, not string
            queue="long",
            timeout=600000
        )
        # msql_error_data_table_migration()

def msql_error_table_migration():
    db = MSSQL()
    error_tables = frappe.db.get_all("Database Table Migration Log",
        filters={
            "table_created": 0
        },
        fields=["table_name", "doctype_name"]
    )
    for table in error_tables:
        table_name = table.get("table_name")
        doctype_name = table.get("doctype_name")
        columns = db.select("""SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = '{0}';
        """.format(table_name))
        if columns:
            frappe.enqueue(
                create_doctype,
                doctype_name=doctype_name,
                columns= columns,
                table_name= table_name,
                queue="long",
                timeout=600000
            )
        else:
            log = frappe.get_doc("Database Table Migration Log", doctype_name)
            log.no_columns = 1
            log.flags.ignore_mandatory = True
            log.flags.ignore_validate = True
            log.flags.ignore_links = True
            log.save(ignore_permissions=True)
            frappe.db.commit()

def msql_error_data_table_migration(page_length=2000):
    error_tables = frappe.db.get_all("Database Table Migration Log",
        filters={
            "table_created": 1,
            "in_progress": 0,
            "data_migrated": 0
            # "name": "mpr-JCDS"
        },
        start=0,
        page_length=page_length,
        fields=["table_name", "doctype_name"],
        order_by='modified desc',
    )
    
    for table in error_tables:
        frappe.db.set_value("Database Table Migration Log", table.get("doctype_name"), "in_progress", 1, update_modified=True)
        frappe.db.commit()
        frappe.enqueue(
            mssql_table_data_migration,
            doctype=table.get("doctype_name"),
            table_name= table.get("table_name"),
            queue="long",
            timeout=600000
        )
        # mssql_table_data_migration(
        #     doctype=table.get("doctype_name"),
        #     table_name= table.get("table_name")
        # )
    frappe.enqueue(
        msql_error_data_table_migration,   # 👈 function reference, not string
        queue="long",
        timeout=600000
    )


def mssql_table_migration():
    db = MSSQL()
    database_tables = db.select("""SELECT *
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE='BASE TABLE' """)
    
    for table in database_tables:
        table_name = table.get("TABLE_NAME")
        doctype_name = f'{table.get("TABLE_SCHEMA")}-{table.get("TABLE_NAME")}'.replace("-/", "-").replace("/", "-")
        if frappe.db.exists("DocType", doctype_name):
            continue
        # columns = db.select("""SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH 
        # 	FROM INFORMATION_SCHEMA.COLUMNS 
        # 	WHERE TABLE_NAME = '{0}';
        # """.format(table_name))
        columns = get_mssql_table_columns(db, table_name)
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

def get_mssql_table_columns(db, table_name):
    columns = db.select("""SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = '{0}';
    """.format(table_name))
    return columns


def create_doctype(doctype_name: str, columns: list, table_name: str):
    doctype = frappe.new_doc("DocType")
    doctype.name = doctype_name
    doctype.module = "Database Table"
    doctype.custom = 1

    doctype_fields = []
    for col in columns:
        fieldtype = convert_mssql_to_frappe(col.get('DATA_TYPE'))
        if col.get('COLUMN_NAME').lower() == "name":
            length = None
            if col.get('CHARACTER_MAXIMUM_LENGTH'):
                length = cint(col.get('CHARACTER_MAXIMUM_LENGTH')) + 1
            doctype_fields.append({
                "label": col.get('COLUMN_NAME'),
                "fieldtype": fieldtype,
                "fieldname": "name2",
                "length": length
            })
        elif col.get('COLUMN_NAME').lower() == "doctype":
            length = None
            if col.get('CHARACTER_MAXIMUM_LENGTH'):
                length = cint(col.get('CHARACTER_MAXIMUM_LENGTH')) + 1
            doctype_fields.append({
                "label": col.get('COLUMN_NAME'),
                "fieldtype": fieldtype,
                "fieldname": "doctype1",
                "length": length
            })
        elif col.get('COLUMN_NAME').lower() == "meta":
            length = None
            if col.get('CHARACTER_MAXIMUM_LENGTH'):
                length = cint(col.get('CHARACTER_MAXIMUM_LENGTH')) + 1
            doctype_fields.append({
                "label": col.get('COLUMN_NAME'),
                "fieldtype": fieldtype,
                "fieldname": "meta1",
                "length": length
            })
        elif col.get('COLUMN_NAME').lower() == "process":
            length = None
            if col.get('CHARACTER_MAXIMUM_LENGTH'):
                length = cint(col.get('CHARACTER_MAXIMUM_LENGTH')) + 1
            doctype_fields.append({
                "label": col.get('COLUMN_NAME'),
                "fieldtype": fieldtype,
                "fieldname": "process1",
                "length": length
            })
        elif col.get('COLUMN_NAME').lower() == "field_order":
            length = None
            if col.get('CHARACTER_MAXIMUM_LENGTH'):
                length = cint(col.get('CHARACTER_MAXIMUM_LENGTH')) + 1
            doctype_fields.append({
                "label": col.get('COLUMN_NAME'),
                "fieldtype": fieldtype,
                "fieldname": "field_order1",
                "length": length
            })
        elif fieldtype == "Data" and col.get('CHARACTER_MAXIMUM_LENGTH'):
            doctype_fields.append({
                "label": col.get('COLUMN_NAME'),
                "fieldtype": fieldtype,
                "length": cint(col.get('CHARACTER_MAXIMUM_LENGTH')) + 1
            })
        else:
            doctype_fields.append({
                "label": col.get('COLUMN_NAME'),
                "fieldtype": fieldtype
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
    log.flags.ignore_mandatory = True
    log.flags.ignore_validate = True
    log.flags.ignore_links = True
    log.save(ignore_permissions=True)

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
    exists_data = frappe.db.get_all(doctype,
        fields=["name"]
    )
    if exists_data:
        frappe.db.sql("delete from `tab{0}`".format(doctype))
        frappe.db.commit()
    # if not db:
    db = MSSQL()
    # create_sync_flag in mssql table
    columns = get_mssql_table_columns(db, table_name)
    sync_flag_exists = False
    for col in columns:
        if col.get('COLUMN_NAME').lower() == "erpnext_is_sync":
            sync_flag_exists = True
            break
    if not sync_flag_exists:
        db.execute("""ALTER TABLE mpr.[{0}]
            ADD erpnext_is_sync INT NOT NULL DEFAULT 0;
        """.format(table_name))

        db.execute("""CREATE INDEX idx_{0}_erpnext_is_sync
            ON mpr.[{1}] (erpnext_is_sync);
        """.format(table_name.replace("/", ""), table_name))

    # primary_key = db.select("""SELECT 
    #         KU.TABLE_NAME,
    #         KU.COLUMN_NAME,
    #         KU.ORDINAL_POSITION,
    #         C.DATA_TYPE
    #     FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS AS TC
    #     JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE AS KU
    #         ON TC.CONSTRAINT_NAME = KU.CONSTRAINT_NAME
    #         AND TC.TABLE_SCHEMA = KU.TABLE_SCHEMA
    #     JOIN INFORMATION_SCHEMA.COLUMNS AS C
    #         ON KU.TABLE_NAME = C.TABLE_NAME
    #         AND KU.COLUMN_NAME = C.COLUMN_NAME
    #         AND KU.TABLE_SCHEMA = C.TABLE_SCHEMA
    #     WHERE TC.TABLE_NAME = '{0}'
    #         AND TC.CONSTRAINT_TYPE = 'PRIMARY KEY'
    #         AND TC.TABLE_SCHEMA = 'mpr'
    #     ORDER BY KU.ORDINAL_POSITION;
    # """.format(table_name))

    primary_key = db.select("""SELECT 
            c.name AS COLUMN_NAME,
            ic.key_ordinal AS ORDINAL_POSITION,
            t.name AS DATA_TYPE
        FROM sys.indexes i
        JOIN sys.index_columns ic 
            ON i.object_id = ic.object_id 
            AND i.index_id = ic.index_id
        JOIN sys.columns c 
            ON ic.object_id = c.object_id 
            AND ic.column_id = c.column_id
        JOIN sys.types t
            ON c.user_type_id = t.user_type_id
        JOIN sys.tables tb
            ON tb.object_id = i.object_id
        JOIN sys.schemas s
            ON tb.schema_id = s.schema_id
        WHERE 
            i.is_primary_key = 1
            AND tb.name = '{0}'
            AND s.name = 'mpr'
        ORDER BY 
            ic.key_ordinal;
    """.format(table_name))

    if not primary_key:
        frappe.throw(f"❌ Primary Key not found for table {table_name}")

    get_mssql_data(db, doctype, table_name, primary_key)

    # frappe.enqueue(
    #     update_data_migration_flag,
    #     doctype=doctype,
    #     queue="long",
    #     timeout=600000
    # )
    update_data_migration_flag(doctype)


def update_data_migration_flag(doctype):
    frappe.db.set_value("Database Table Migration Log", doctype, "data_migrated", 1, update_modified=True)
    # frappe.enqueue(
    #     msql_error_data_table_migration,   # 👈 function reference, not string
    #     page_length=1,
    #     queue="long",
    #     timeout=600000
    # )
    # log = frappe.get_doc("Database Table Migration Log", doctype)
    # log.data_migrated = 1
    # log.flags.ignore_mandatory = True
    # log.flags.ignore_validate = True
    # log.flags.ignore_links = True
    # log.save(ignore_permissions=True)


def get_mssql_data(db, doctype, table_name, primary_key):
    pk_condition = ""
    if primary_key:
        pk_condition = " AND ".join(
            (
                f"[{col.get('COLUMN_NAME')}] = {{{col.get('COLUMN_NAME')}}}"
                if col.get("DATA_TYPE") == "varbinary"
                else f"[{col.get('COLUMN_NAME')}] = '{{{col.get('COLUMN_NAME')}}}'"
            )
            for col in primary_key
        )

    db.execute("""UPDATE mpr.[{0}]
        SET erpnext_is_sync = 0 WHERE erpnext_is_sync = 1;""".format(table_name))

    db.execute("""UPDATE mpr.[{0}]
        SET erpnext_is_sync = 0 WHERE erpnext_is_sync = 2;""".format(table_name))

    while True:
        records = db.select(
            """SELECT TOP 1000 * FROM mpr.[{0}] WHERE erpnext_is_sync = 0;""".format(
                table_name
            )
        )
        # frappe.log_error(str(records), "Sap migration data table")
        # stop loop if no rows
        if not records:
            break
        for record in records:
            update_sync_flag(db, table_name, pk_condition, record, 2)
        # frappe.enqueue(
        #     create_data_in_frappe,
        #     doctype=doctype,
        #     table_name=table_name,
        #     pk_condition=pk_condition,
        #     records=records,
        #     queue="long",
        #     timeout=600000,
        # )
        create_data_in_frappe(doctype, table_name, pk_condition, records)


def create_data_in_frappe(doctype, table_name, pk_condition, records):
    db = MSSQL()
    user = frappe.session.user
    fields = [
        "name",
        "creation",
        "modified",
        "owner",
        "modified_by"
    ]
    insert_data = []

    if records:
        for key, value in records[0].items():
            field_name = key.strip().lower().replace(" ", "_").strip("?").replace("/", "")
            
            if field_name == "name":
                field_name = "name2"
            elif field_name == "doctype":
                field_name = "doctype1"
            elif field_name == "meta":
                field_name = "meta1"
            elif field_name == "process":
                field_name = "process1"
            elif field_name == "field_order":
                field_name = "field_order1"
            elif field_name in restricted:
                field_name = field_name + "1"
            if not isinstance(value, (bytes, bytearray)) and field_name != "erpnext_is_sync":
                fields.append(field_name)

        for record in records:
            values = (
                make_autoname("hash", doctype),
                now(),
                now(),
                user,
                user
            )

            for key, value in record.items():
                if not isinstance(value, (bytes, bytearray)) and key != "erpnext_is_sync":
                    values = values + (value,)
            insert_data.append(values)

        frappe.db.bulk_insert(doctype, fields=fields, values=set(insert_data))

        for record in records:
            # update sync flag
            update_sync_flag(db, table_name, pk_condition, record, 1)
        frappe.db.commit()
                    

    

    # for record in records:
    # 	file_dict = []
    # 	doc = frappe.new_doc(doctype)
    # 	for key, value in record.items():
    # 		field_name = key.strip().lower().replace(" ", "_").strip("?")
            
    # 		if field_name == "name":
    # 			field_name = "name2"
    # 		elif field_name == "doctype":
    # 			field_name = "doctype1"
    # 		elif field_name == "meta":
    # 			field_name = "meta1"
    # 		elif field_name == "process":
    # 			field_name = "process1"
    # 		elif field_name == "field_order":
    # 			field_name = "field_order1"
    # 		elif field_name in restricted:
    # 			field_name = field_name + "1"
    # 		if isinstance(value, (bytes, bytearray)):
    # 			file_dict.append({field_name: value})
    # 		else:
    # 			doc.set(field_name, value)
    # 	doc.flags.ignore_mandatory = True
    # 	doc.flags.ignore_validate = True
    # 	doc.flags.ignore_links = True
    # 	doc.insert(ignore_permissions=True)
        
    # 	if file_dict:
    # 		for file in file_dict:
    # 			for key, value in file.items():
    # 				# frappe.error_log(str(value), "File Value")
    # 				# print(value)
    # 				encoded_data = base64.b64encode(value)
    # 				# frappe.error_log(str(encoded_data), "Encoded File Value")
    # 				# print(encoded_data)
    # 				# Create file in Frappe
    # 				file_doc = frappe.get_doc({
    # 					"doctype": "File",
    # 					"file_name": key,
    # 					"attached_to_doctype": doc.doctype,
    # 					"attached_to_name": doc.name,
    # 					"attached_to_field": key,
    # 					"content": encoded_data,     # base64 string
    # 					"decode": True,              # auto-decodes base64
    # 					"is_private": 1,
    # 					"folder": "Home/Attachments"
    # 				})
    # 				file_doc.flags.ignore_mandatory = True
    # 				file_doc.flags.ignore_validate = True
    # 				file_doc.flags.ignore_links = True
    # 				file_doc.insert(ignore_permissions=True)
    # 				doc.set(key, file_doc.file_url)
    # 		doc.save(ignore_permissions=True)

    # 	# update sync flag
    # 	update_sync_flag(db, table_name, pk_condition, record, 1)
    # 	frappe.db.commit()


def update_sync_flag(db, table_name, pk_condition, record, flag):
    cond_values = record.copy()
    for c in cond_values:
        if isinstance(cond_values[c], (bytes, bytearray)):
            cond_values[c] = '0x' + cond_values[c].hex()
        elif isinstance(cond_values[c], str):
            cond_values[c] = cond_values[c].replace("'", "''")

    mssql_query = f"""UPDATE mpr.[{table_name}]
        SET erpnext_is_sync = {flag}
        WHERE {pk_condition};"""
    db.execute(mssql_query.format(**cond_values))
