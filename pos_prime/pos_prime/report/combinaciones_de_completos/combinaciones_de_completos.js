// Copyright (c) 2026, Ravindu Gajanayaka
// Licensed under GPLv3. See license.txt

frappe.query_reports["Combinaciones de Completos"] = {
	filters: [
		{
			fieldname: "combo",
			label: __("Combo"),
			fieldtype: "Link",
			options: "Restaurant Combo",
			reqd: 1,
		},
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
	],
};
