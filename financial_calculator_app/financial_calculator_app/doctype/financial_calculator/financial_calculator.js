frappe.ui.form.on('Financial Calculator', {
    refresh: function(frm) {
        // Add calculate button if not already present
        if(frm.is_new()) {
            frm.add_custom_button(__('Calculate UK Investor'), function() {
                calculate_uk_investor(frm);
            });
            
            // Button for International Investor
            frm.add_custom_button(__('Calculate International Investor'), function() {
                calculate_int_investor(frm);
            });
            
            frm.calculator_setup = true;
            // frm.add_custom_button(__('Calculate'), function() {
            //     let required_fields = [
            //         'purchase_price', 'renovation', 'architectplanning',
            //         'building_control', 'furniture', 'survey',
            //         'legals', 'insurance', 'sourcing', 'sdlt',
            //         'rooms', 'rentm_rm_rate_reverse_calc', 'asking_price'
            //     ];
                
            //     let missing_fields = [];
            //     required_fields.forEach(function(field) {
            //         if (!frm.doc[field]) {
            //             missing_fields.push(frappe.unscrub(field));
            //         }
            //     });
                
            //     if (missing_fields.length > 0) {
            //         frappe.throw(__('Please fill these required fields first: ') + missing_fields.join(', '));
            //         return;
            //     }
                
            //     frm.call('run_calculations').then(() => {
            //         frm.refresh();
            //         frappe.show_alert({message: __('Calculations completed'), indicator:'green'});
            //     });
            // });
            // frm.calculator_setup = true;
        }
    },

    // Field change handlers
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
    int_renovation: function(frm) {
        if (frm.doc.int_renovation) {
            frm.call('calculate_project_management').then(() => {
                frm.refresh_field('project_management');
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
        // if (frm.doc.int_sdlt) {
        //     frm.call('calculate_sdlt_amount').then(() => {
        //         frm.refresh_field('int_sdlt_amount');
        //     });
        // }

        if (frm.doc.int_purchase_price) {
            frm.call('calculate_all').then(() => {
                frm.refresh_fields(['int_sdlt_amount', 'lending_and_brokerage_fees']);
            });
        }
    }
    // int_purchase_price: function(frm) {
    //     // Calculate both values in parallel
    //     Promise.all([
    //         frm.doc.int_sdlt ? frm.call('calculate_sdlt_amount') : Promise.resolve(),
    //         frm.call('calculate_lending_and_brokerage_fees')
    //     ]).then(() => {
    //         frm.refresh_fields(['int_sdlt_amount', 'lending_and_brokerage_fees']);
    //     });
    // }
});

function calculate_uk_investor(frm) {
    let required_fields = [
        'purchase_price', 'renovation', 'architectplanning',
        'building_control', 'furniture', 'survey',
        'legals', 'insurance', 'sourcing', 'sdlt',
        'rooms', 'rentm_rm_rate_reverse_calc', 'asking_price'
    ];
    
    let missing_fields = [];
    required_fields.forEach(function(field) {
        if (!frm.doc[field]) {
            missing_fields.push(frappe.unscrub(field));
        }
    });
    
    if (missing_fields.length > 0) {
        frappe.throw(__('Please fill these required fields first: ') + missing_fields.join(', '));
        return;
    }
    
    // Pass the investor type to the server method
    frm.call('run_calculations').then(() => {
                frm.refresh();
                frappe.show_alert({message: __('Calculations completed'), indicator:'green'});
            });
}

function calculate_int_investor(frm, investor_type) {
    let required_fields = [
        'int_purchase_price','int_renovation', 'int_architectplanning',
        'int_building_control', 'int_furniture', 'int_survey',
        'int_legals', 'int_insurance', 'int_sourcing', 'int_sdlt',
        'int_asking_price','int_rooms'
    ];
    
    let missing_fields = [];
    required_fields.forEach(function(field) {
        if (!frm.doc[field]) {
            missing_fields.push(frappe.unscrub(field));
        }
    });
    
    if (missing_fields.length > 0) {
        frappe.throw(__('Please fill these required fields first: ') + missing_fields.join(', '));
        return;
    }
    
    // Pass the investor type to the server method
    frm.call('run_calculations_int').then(() => {
        frm.refresh();
        frappe.show_alert({message: __('Calculations completed'), indicator:'green'});
    });
}