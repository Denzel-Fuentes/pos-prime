// Copyright (c) 2026, Ravindu Gajanayaka
// Licensed under GPLv3. See license.txt

frappe.ui.form.on("Restaurant Order", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1) return;

		frm.add_custom_button(__("Reprint Kitchen Ticket"), () => {
			frappe.call({
				method: "pos_prime.api.restaurant.reprint_comanda",
				args: { restaurant_order: frm.doc.name },
				freeze: true,
				freeze_message: __("Printing..."),
				callback: (r) => {
					frm.reload_doc();
					const status = r.message && r.message.comanda_status;
					if (status === "Printed") {
						frappe.show_alert({ message: __("Kitchen ticket printed."), indicator: "green" });
					} else {
						frappe.show_alert({
							message: __("Kitchen ticket failed: {0}", [
								(r.message && r.message.comanda_error) || status || "",
							]),
							indicator: "red",
						});
					}
				},
			});
		});
	},
});
