// Copyright (c) 2026, Ravindu Gajanayaka
// Licensed under GPLv3. See license.txt

frappe.ui.form.on("Restaurant Printer", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__("Test Printer"), () => {
			frappe.call({
				method: "pos_prime.api.restaurant.test_printer",
				args: { printer: frm.doc.name },
				freeze: true,
				freeze_message: __("Printing test ticket..."),
				callback: () => {
					frappe.show_alert({ message: __("Test ticket sent."), indicator: "green" });
				},
			});
		});
	},
});
