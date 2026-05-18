// Copyright (c) 2025, Digitalis Technologies Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("SAP Integration", {
    refresh(frm) {
        frm.add_custom_button(__("Migrate Database Tables"), () =>
            frm.call("migrate_database").then(() =>
                frappe.msgprint("Database Migration Initiated Successfully!")
            ), __('Migrate')
        );
        frm.add_custom_button(__("Drop Error Tables"), () =>
            frm.call("drop_error_tables").then(() =>
                frappe.msgprint("Drop Tables Successfully!")
            ), __('Migrate')
        );
        frm.add_custom_button(__("Migrate Error Tables"), () =>
            frm.call("migrate_error_tables").then(() =>
                frappe.msgprint("Error Tables Migration Initiated Successfully!")
            ), __('Migrate')
        );
        frm.add_custom_button(__("Migrate Data Table"), () =>
            frm.call("migrate_error_data_tables").then(() =>
                frappe.msgprint("Error Data Tables Migration Initiated Successfully!")
            ), __('Migrate')
        );
        frm.add_custom_button(__("Compare Data Table"), () =>
            frm.call("compare_data_tables").then(() =>
                frappe.msgprint("Data Tables Comparison Initiated Successfully!")
            ), __('Tools')
        );
        frm.add_custom_button(__("Lock Migrated Tables"), () =>
            frm.call("lock_migrated_tables").then(() =>
                frappe.msgprint("Migrated Tables Locked Successfully!")
            ), __('Tools')
        );
        frm.add_custom_button(__("Update English Description"), () =>
            frm.call("update_english_description").then(() =>
                frappe.msgprint("English Description Updated Successfully!")
            ), __('Tools')
        );
        
    },
});
