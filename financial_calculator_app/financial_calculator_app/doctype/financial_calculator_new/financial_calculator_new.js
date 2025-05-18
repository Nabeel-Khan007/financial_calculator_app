frappe.ui.form.on('Financial Calculator New', {
    opportunity: function(frm) {
        if (frm.doc.opportunity) {
            // Fetch Opportunity details
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Opportunity',
                    name: frm.doc.opportunity
                },
                callback: function(response) {
                    if (response.message) {
                        const opp = response.message;
                        // Set Forecast Name = "Opportunity Name - Address"
                        frm.set_value('forecast_name', `${opp.name} - ${opp.custom_address || ''}`);
                    }
                }
            });
        } else {
            // Clear if no Opportunity selected
            frm.set_value('forecast_name', '');
        }
    },
    project: function(frm) {
        if (frm.doc.project) {
            // Fetch Opportunity details
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Project',
                    name: frm.doc.project
                },
                callback: function(response) {
                    if (response.message) {
                        const project = response.message;
                        // Set Forecast Name = "Opportunity Name - Address"
                        frm.set_value('forecast_name', `${project.name} - ${project.custom_address || ''}`);
                    }
                }
            });
        } else {
            // Clear if no Opportunity selected
            frm.set_value('forecast_name', '');
        }
    },
    refresh: function(frm) {
        // Add single calculate button if not already present frm.is_new()
        // if(!frm.calculator_setup) {
            frm.add_custom_button(__('Calculate'), function() {
                calculate_all(frm);
            });
            frm.calculator_setup = true;
        // }
    },

    // Field change handlers (keep your existing ones)
    sdlt: function(frm) {
        if (frm.doc.purchase_price) {
            frm.call('calculate_sdlt').then(() => {
                frm.refresh_field('sdlt_amount');
            });
        }
    },
    purchase_price: function(frm) {
        if (frm.doc.sdlt) {
            frm.call('calculate_sdlt').then(() => {
                frm.refresh_field('sdlt_amount');
            });
        }
    },
    main_renovation: function(frm) {
        if (frm.doc.main_renovation) {
            frm.call('calculate_project_management').then(() => {
                frm.refresh_field('main_project_management');
            });
        }
    },
    main_project_management_percentage: function(frm) {
        if (frm.doc.main_project_management_percentage) {
            frm.call('calculate_project_management').then(() => {
                frm.refresh_field('main_project_management');
            });
        }
    },
    main_rooms: function(frm) {
        if (frm.doc.main_rooms && frm.doc.main_rentm_rm_rate_reverse_calc) {
            frm.call('calculate_main_average_ratewk').then(() => {
                frm.refresh_field('main_average_ratewk');
            });
        }

        if (frm.doc.main_rooms && frm.doc.main_average_ratewk) {
            frm.call('calculate_rent').then(() => {
                frm.refresh_field('main_rentm_rm_rate_reverse_calc');
            });
        }
    },
    main_rentm_rm_rate_reverse_calc: function(frm) {
        if (frm.doc.main_rentm_rm_rate_reverse_calc) {
            frm.set_value('main_lease_setup', frm.doc.main_rentm_rm_rate_reverse_calc);
        }
        
        if (frm.doc.main_rooms && frm.doc.main_rentm_rm_rate_reverse_calc) {
            frm.call('calculate_main_average_ratewk').then(() => {
                frm.refresh_field('main_average_ratewk');
            });
        }
    },
    main_average_ratewk: function(frm) {
        if (frm.doc.main_rooms && frm.doc.main_average_ratewk) {
            frm.call('calculate_rent').then(() => {
                // frm.refresh_field('main_rentm_rm_rate_reverse_calc');
                frm.refresh_fields(['main_rentm_rm_rate_reverse_calc', 'main_lease_setup']);
            });
        }
    },
    int_sdlt: function(frm) {
        if (frm.doc.int_purchase_price) {
            frm.call('calculate_sdlt_amount').then(() => {
                frm.refresh_field('int_sdlt_amount');
            });
        }
    },
    int_purchase_price: function(frm) {
        if (frm.doc.int_purchase_price) {
            frm.call('calculate_all').then(() => {
                frm.refresh_fields(['int_sdlt_amount', 'lending_and_brokerage_fees']);
            });
        }
    }
});

function calculate_all(frm) {
    // First validate all required fields in details tab
    let required_fields = [
        'main_asking_price', 'main_purchase_price', 'main_renovation',
        'main_rooms', 'main_rentm_rm_rate_reverse_calc','main_gross_development_value','main_average_ratewk','main_sdlt'
    ];
    
    let missing_fields = [];
    required_fields.forEach(function(field) {
        if (!frm.doc[field]) {
            missing_fields.push(frappe.unscrub(field));
        }
    });
    
    if (missing_fields.length > 0) {
        frappe.throw(__('Please fill these required fields in Details tab first: ') + missing_fields.join(', '));
        return;
    }
    
    // Call server method that will:
    // 1. Copy values from details to UK investor
    // 2. Perform all calculations
    frm.call('run_calculations').then(() => {
        frm.refresh();
        frappe.show_alert({message: __('All calculations completed'), indicator:'green'});
    });
}