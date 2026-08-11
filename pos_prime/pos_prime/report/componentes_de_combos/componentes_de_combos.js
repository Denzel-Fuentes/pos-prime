// Copyright (c) 2026, Ravindu Gajanayaka
// Licensed under GPLv3. See license.txt

frappe.query_reports["Componentes de Combos"] = {
	onload(report) {
		report.page.add_inner_message(
			__("Qué item se elige en cada slot de cada combo, y con qué frecuencia — para detectar el componente más popular por slot.")
		);
	},
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
	],
};
