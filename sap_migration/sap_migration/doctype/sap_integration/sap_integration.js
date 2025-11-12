// Copyright (c) 2025, Digitalis Technologies Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("SAP Integration", {
    refresh(frm) {
        frm.add_custom_button(__("Migrate Database"), () =>
            frm.call("migrate_database").then(() =>
                frappe.msgprint("Database Migration Initiated Successfully!")
            )
        );
    },
});
