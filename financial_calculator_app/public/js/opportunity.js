frappe.provide("financial_calculator_app");

financial_calculator_app.Opportunity = class Opportunity extends erpnext.crm.Opportunity {
    refresh() {
        this.show_notes();  // enables comments section
    }
};

extend_cscript(cur_frm.cscript, new financial_calculator_app.Opportunity({ frm: cur_frm }));