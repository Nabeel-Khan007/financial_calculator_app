from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import re

class FinancialCalculator(Document):
    def validate(self):
        if not hasattr(self, '_is_calculating'):
            self.calculate_sdlt()
            self.calculate_acquisition_costs()
            self.calculate_post_works_refinance()
            self.calculate_rental_income()
            self.calculate_capital_growth()
            self.calculate_capital_gain()
            self.calculate_returns()
            # intternational_investor
            self.calculate_sdlt_amount()
            self.calculate_lending_and_brokerage_fees()
            self.calculate_project_management()
            self.calculate_acquisition_costs_int()
            self.calculate_post_works_refinance_int()
            self.calculate_rental_income_int()
            self.calculate_capital_growth_int()
            self.calculate_capital_gain_int()
            self.calculate_returns_int()
    
    def clean_currency(self, value):
        """Convert currency string to float by removing all non-numeric characters"""
        if value is None or value == "":
            return 0
        if isinstance(value, str):
            # Remove all non-numeric characters except decimal point
            value = re.sub(r'[^\d.]', '', value)
            try:
                return float(value) if value else 0
            except ValueError:
                return 0
        return float(value)
    
    def calculate_acquisition_costs(self):
        """Calculate all acquisition cost related fields"""
        fields_to_sum = [
            'purchase_price',
            'renovation',
            'architectplanning',
            'building_control',
            'furniture',
            'survey',
            'legals',
            'insurance',
            'sourcing',
            'sdlt_amount'  # Include SDLT in total costs
        ]
        
        total = 0
        for field in fields_to_sum:
            value = getattr(self, field, None)
            total += self.clean_currency(value)
        
        self.capital_in = total
    
    @frappe.whitelist()
    def calculate_sdlt(self):
        """Calculate SDLT based on property type and purchase price"""
        if not self.sdlt or not self.purchase_price:
            self.sdlt_amount = 0
            return
            
        purchase_price = self.clean_currency(self.purchase_price)
        
        if self.sdlt == "Resi":
            self.sdlt_amount = self.calculate_residential_sdlt(purchase_price)
        elif self.sdlt in ["Non-Resi", "Mixed-Use", "Land"]:
            self.sdlt_amount = self.calculate_non_residential_sdlt(purchase_price)
        else:  # Exempt or Chain-Break
            self.sdlt_amount = 0
    
    def calculate_residential_sdlt(self, price):
        """Calculate residential SDLT"""
        if price <= 40000:
            return 0
        elif 40001 <= price <= 125000:
            return price * 0.05
        elif 125001 <= price <= 250000:
            return (price - 125000) * 0.07 + 6250
        elif 250001 <= price <= 925000:
            return (price - 250000) * 0.10 + 6250 + 8750
        elif 925001 <= price <= 1500000:
            return (price - 925000) * 0.15 + 6250 + 8750 + 67500
        else:  # Above 1.5M
            return (price - 1500000) * 0.17 + 6250 + 8750 + 67500 + 86250
    
    def calculate_non_residential_sdlt(self, price):
        """Calculate non-residential SDLT"""
        if price <= 150000:
            return 0
        elif 150001 <= price <= 250000:
            return price * 0.02
        else:  # Above 250k
            return (price - 250000) * 0.05 + 2000
    
    @frappe.whitelist()
    def run_calculations(self):
        """Method called by the calculate button"""
        self._is_calculating = True
        self.calculate_sdlt()
        self.calculate_acquisition_costs()
        self.calculate_post_works_refinance()
        self.calculate_rental_income()
        self.calculate_capital_growth()
        self.calculate_capital_gain()
        self.calculate_returns()

        doc_dict = self.as_dict()
        return doc_dict

    def calculate_post_works_refinance(self):
        """Calculate post works refinance section"""
        # Gross Development Value comes from Asking Price
        self.gross_development_value = self.clean_currency(self.asking_price or 0)
        
        # Uplift is difference between Asking Price and Purchase Price
        self.uplift = self.gross_development_value - self.clean_currency(self.purchase_price or 0)
        
        # 1st Charge Lending (75% of Gross Development Value)
        self.first_charge_lending = self.gross_development_value * 0.75

        self.first_charge_lending_ltv = 75
        
        # Calculate total investment (same as capital_in)
        total_investment = self.clean_currency(self.purchase_price or 0) + \
                          self.clean_currency(self.renovation or 0) + \
                          self.clean_currency(self.architectplanning or 0) + \
                          self.clean_currency(self.building_control or 0) + \
                          self.clean_currency(self.furniture or 0) + \
                          self.clean_currency(self.sdlt_amount or 0) + \
                          self.clean_currency(self.survey or 0) + \
                          self.clean_currency(self.legals or 0) + \
                          self.clean_currency(self.insurance or 0) + \
                          self.clean_currency(self.sourcing or 0)
        
        # Capital Left In is total investment minus capital released
        self.capital_left_in = total_investment - self.first_charge_lending
        
        # Capital Released equals 1st Charge Lending
        self.capital_released = self.first_charge_lending
        
    @frappe.whitelist()
    def calculate_rental_income(self):
        """Calculate all rental income related fields"""
        try:
            # Convert input fields to proper numeric values
            rooms = float(self.rooms) if self.rooms else 0
            rent_per_month = self.clean_currency(self.rentm_rm_rate_reverse_calc or 0)
            
            # Calculate weekly rent per room (monthly × 12 ÷ 52 ÷ rooms)
            self.average_ratewk = round((rent_per_month * 12) / 52 / rooms if rooms else 0,2)

            average_ratefield = (rent_per_month * 12) / 52 / rooms if rooms else 0
            
            # Calculate annual gross rent (rooms × weekly rate × 52 weeks)
            self.gross_rent_pa = rooms * average_ratefield * 52
            
            # Calculate mortgage payments (6% of first_charge_lending)
            mortgage_rate = 0.06  # 6%
            self.mortgage_pa = self.clean_currency(self.first_charge_lending or 0) * mortgage_rate
            
            # Operational expenses (0% of gross rent)
            self.operational_expenses_pa = 0.00
            
            # Management fees (0% of gross rent)
            self.management_pa = 0.00

            # Calculate net cash flow - no rounding
            self.net_cash_flow_pa = (
                self.gross_rent_pa - 
                self.mortgage_pa - 
                self.operational_expenses_pa - 
                self.management_pa
            )
            
        except Exception as e:
            frappe.log_error(f"Error in rental income calculation: {str(e)}")
            # Set defaults if calculation fails
            self.average_ratewk = 0.00
            self.gross_rent_pa = 0.00
            self.mortgage_pa = 0.00
            self.operational_expenses_pa = 0.00
            self.management_pa = 0.00
            self.net_cash_flow_pa = 0.00

    def calculate_capital_growth(self):
        """Calculate capital growth with static 3.5% growth rate and populate child table"""
        try:
            # Clear existing table
            self.capital_growth_table = []
            
            if not self.asking_price:
                frappe.msgprint("Please enter an Asking Price to see capital growth projections")
                return
            
            current_value = self.clean_currency(self.asking_price)
            if current_value <= 0:
                frappe.msgprint("Please enter a valid positive Asking Price")
                return
            
            growth_rate = 0.035  # Static 3.5% growth rate
            
            # Populate child table with growth data
            for year in range(0, 11):
                increase = current_value * growth_rate
                display_value = round(current_value)
                current_value += increase
                # display_value = current_value
                display_increase = round(increase) if year < 10 else None
                # if year == 0:
                #     increase = 0
                #     display_value = current_value
                #     display_increase = 0
                # else:
                #     increase = current_value * growth_rate
                #     current_value += increase
                #     display_value = current_value
                #     display_increase = increase
                
                self.append("capital_growth_table", {
                    "year": year,
                    "value": "{:,.0f}".format(display_value),
                    "growth_rate": growth_rate * 100 if year < 10 else 0,
                    "increase": "{:,.0f}".format(display_increase) if display_increase is not None else None
                })
        
        except Exception as e:
            frappe.log_error(f"Error in calculate_capital_growth: {str(e)}")
            frappe.msgprint(f"Error generating capital growth table: {str(e)}")

    def calculate_capital_gain(self):
        """Calculate capital gain and populate child table"""
        try:
            # Clear existing table
            self.capital_gain_table = []
            
            if not self.asking_price:
                frappe.msgprint("Please enter an Asking Price to see capital gain projections")
                return
            
            current_value = self.clean_currency(self.asking_price)
            growth_rate = 0.035  # 3.5% growth rate
            
            # Calculate 10-year projection
            capital_value_10yr = current_value * (1 + growth_rate)**10
            mortgage_lending = self.first_charge_lending
            equity_investment = self.capital_left_in
            capital_gain = capital_value_10yr - mortgage_lending - equity_investment

            formatted_capital_value_10yr = "{:,.0f}".format(round(capital_value_10yr))
            formatted_mortgage_lending = "{:,.0f}".format(round(mortgage_lending))
            formatted_equity_investment = "{:,.0f}".format(round(equity_investment))
            formatted_capital_gain = "{:,.0f}".format(round(capital_gain))
            
            # Populate child table
            self.append("capital_gain_table", {
                "description": "Capital Value @ Year 10",
                "amount": formatted_capital_value_10yr
            })
            
            self.append("capital_gain_table", {
                "description": "Mortgage Lending",
                "amount": formatted_mortgage_lending
            })
            
            self.append("capital_gain_table", {
                "description": "Equity Investment Capital",
                "amount": formatted_equity_investment
            })
            
            self.append("capital_gain_table", {
                "description": "Capital Gain @ Year 10",
                "amount": formatted_capital_gain
            })
        
        except Exception as e:
            frappe.log_error(f"Error in calculate_capital_gain: {str(e)}")
            frappe.msgprint(f"Error generating capital gain table: {str(e)}")

    def calculate_returns(self):
        """Calculate investment returns metrics and populate child table"""
        try:
            # Clear existing table
            self.returns_table = []
            
            # Ensure we have all required values
            if None in [self.capital_left_in, self.net_cash_flow_pa, self.first_charge_lending, self.asking_price]:
                frappe.msgprint("Please complete all calculations first")
                return
                
            # Convert to floats for calculation
            retained_capital = float(self.capital_left_in or 0)
            annual_cashflow = float(self.net_cash_flow_pa or 0)
            
            # Calculate capital gain
            growth_rate = 0.035  # 3.5% growth
            current_value = self.clean_currency(self.asking_price or 0)
            capital_value_10yr = current_value * (1 + growth_rate)**10
            capital_gain = capital_value_10yr - float(self.first_charge_lending or 0) - retained_capital
            
            # Calculate returns metrics
            lifetime_cashflow = annual_cashflow * 10  # 10 years projection
            total_return = lifetime_cashflow + capital_gain
            
            # ROI Calculations
            # annualized_roi = (annual_cashflow / retained_capital) * 100 if retained_capital else 0
            # lifetime_roi = (total_return / retained_capital) * 100 if retained_capital else 0
            annualized_roi = round((annual_cashflow / retained_capital) * 100, 2) if retained_capital else 0
            lifetime_roi = round((total_return / retained_capital) * 100, 2) if retained_capital else 0

            formatted_retained_capital = "{:,.0f}".format(round(retained_capital))
            formatted_annual_cashflow = "{:,.0f}".format(round(annual_cashflow))
            formatted_lifetime_cashflow = "{:,.0f}".format(round(lifetime_cashflow))
            formatted_capital_gain = "{:,.0f}".format(round(capital_gain))
            formatted_total_return = "{:,.0f}".format(round(total_return))
            
            # Populate child table
            self.append("returns_table", {
                "metric": "Retained Capital",
                "value": formatted_retained_capital,
                "percentage": 0
            })
            
            self.append("returns_table", {
                "metric": "Net Cash Flow PA",
                "value": formatted_annual_cashflow,
                "percentage": 0
            })
            
            self.append("returns_table", {
                "metric": "Total Net Lifetime Cash Flow",
                "value": formatted_lifetime_cashflow,
                "percentage": 0
            })
            
            self.append("returns_table", {
                "metric": "Capital Gain @ Year 10",
                "value": formatted_capital_gain,
                "percentage": 0
            })
            
            self.append("returns_table", {
                "metric": "Total Lifetime Return on Capital",
                "value": formatted_total_return,
                "percentage": 0
            })
            
            self.append("returns_table", {
                "metric": "Annualised ROI",
                "value": 0,
                "percentage": annualized_roi
            })
            
            self.append("returns_table", {
                "metric": "Lifetime Return",
                "value": 0,
                "percentage": lifetime_roi
            })
        
        except Exception as e:
            frappe.log_error(f"Error in calculate_returns: {str(e)}")
            frappe.msgprint(f"Error calculating returns: {str(e)}")

    # international investor working
    @frappe.whitelist()
    def run_calculations_int(self):
        """Method called by the calculate button"""
        self._is_calculating = True
        # self.calculate_sdlt_amount()
        self.calculate_sdlt_amount()
        self.calculate_lending_and_brokerage_fees()
        self.calculate_project_management()
        self.calculate_acquisition_costs_int()
        self.calculate_post_works_refinance_int()
        self.calculate_rental_income_int()
        self.calculate_capital_growth_int()
        self.calculate_capital_gain_int()
        self.calculate_returns_int()

        doc_dict = self.as_dict()
        return doc_dict

    def calculate_acquisition_costs_int(self):
        """Calculate all acquisition cost related fields"""
        fields_to_sum = [
            'int_purchase_price',
            'int_renovation',
            'int_architectplanning',
            'int_building_control',
            'int_furniture',
            'int_survey',
            'int_legals',
            'int_insurance',
            'int_sourcing',
            'int_sdlt_amount',
            'project_management',
            'lease_setup',
            'lending_and_brokerage_fees'
        ]
        
        total = 0
        for field in fields_to_sum:
            value = getattr(self, field, None)
            total += self.clean_currency(value)
        
        self.int_capital_in = total

    @frappe.whitelist()
    def calculate_project_management(self):
        if self.int_renovation:
            self.project_management = self.clean_currency(self.int_renovation) * 0.10

    @frappe.whitelist()
    def calculate_all(self):
        self.calculate_lending_and_brokerage_fees()
        self.calculate_sdlt_amount()

    @frappe.whitelist()
    def calculate_lending_and_brokerage_fees(self):
        try:
            if not hasattr(self, 'int_purchase_price') or not self.int_purchase_price:
                self.lending_and_brokerage_fees = 0
                return
            
            # purchase_price = flt(self.int_purchase_price)
            price_lending = self.clean_currency(self.int_purchase_price)
            ltv_ratio = 0.75  # 75% LTV ratio
            
            # Calculate loan amount (B21 * G22)
            loan_amount = price_lending * ltv_ratio
            
            # Fixed fees
            fixed_fees = 600 + 500 + 350 + 1500  # Sum of all fixed components
            
            # Percentage-based fees (2% + 1% = 3% total of loan amount)
            percentage_fees = loan_amount * 0.03
            
            # Total lending fees
            total_fees = fixed_fees + percentage_fees

            self.lending_and_brokerage_fees = round(total_fees, 2)

        except Exception as e:
            frappe.log_error(f"Failed to calculate lending fees: {str(e)}")
            self.lending_and_brokerage_fees = 0

    @frappe.whitelist()
    def calculate_sdlt_amount(self):
        """Calculate SDLT amount based on property type and purchase price"""
        if not self.int_purchase_price or not self.int_sdlt:
            self.int_sdlt_amount = 0
            return
        
        price = self.clean_currency(self.int_purchase_price)
        
        if self.int_sdlt in ["Exempt", "Chain-Break"]:
            self.int_sdlt_amount = 0
        
        elif self.int_sdlt == "Resi":
            # Residential property SDLT calculation
            if price <= 40000:
                self.int_sdlt_amount = 0
            elif price <= 125000:
                self.int_sdlt_amount = price * 0.07
            elif price <= 250000:
                self.int_sdlt_amount = 8750 + (price - 125000) * 0.09
            elif price <= 925000:
                self.int_sdlt_amount = 8750 + 11250 + (price - 250000) * 0.12
            elif price <= 1500000:
                self.int_sdlt_amount = 8750 + 11250 + 81000 + (price - 925000) * 0.17
            else:
                self.int_sdlt_amount = 8750 + 11250 + 81000 + 97750 + (price - 1500000) * 0.19
        
        else:  # Non-Resi, Mixed-Use, Land
            if price <= 150000:
                self.int_sdlt_amount = 0
            elif price <= 250000:
                self.int_sdlt_amount = price * 0.02
            else:
                self.int_sdlt_amount = 2000 + (price - 250000) * 0.05
        
        # Round to 2 decimal places
        self.int_sdlt_amount = round(self.int_sdlt_amount, 2)

    def calculate_post_works_refinance_int(self):
        """Calculate post works refinance section"""
        # Gross Development Value comes from Asking Price
        self.int_gross_development_value = self.clean_currency(self.int_asking_price or 0)
        
        # Uplift is difference between Asking Price and Purchase Price
        self.int_uplift = self.int_gross_development_value - self.clean_currency(self.int_purchase_price or 0)
        
        # 1st Charge Lending (75% of Gross Development Value)
        self.int_first_charge_lending = self.int_gross_development_value * 0.75

        self.int_first_charge_lending_ltv = 75
        
        # Calculate total investment (same as capital_in)
        total_investment = self.clean_currency(self.int_purchase_price or 0) + \
                          self.clean_currency(self.int_renovation or 0) + \
                          self.clean_currency(self.int_architectplanning or 0) + \
                          self.clean_currency(self.int_building_control or 0) + \
                          self.clean_currency(self.int_furniture or 0) + \
                          self.clean_currency(self.int_sdlt_amount or 0) + \
                          self.clean_currency(self.int_survey or 0) + \
                          self.clean_currency(self.int_legals or 0) + \
                          self.clean_currency(self.int_insurance or 0) + \
                          self.clean_currency(self.int_sourcing or 0) + \
                          self.clean_currency(self.project_management or 0) + \
                          self.clean_currency(self.lease_setup or 0) + \
                          self.clean_currency(self.lending_and_brokerage_fees or 0)

        
        # Capital Left In is total investment minus capital released
        self.int_capital_left_in = total_investment - self.int_first_charge_lending
        
        # Capital Released equals 1st Charge Lending
        self.int_capital_released = total_investment - self.int_capital_left_in

    @frappe.whitelist()
    def calculate_rental_income_int(self):
        """Calculate all rental income related fields"""
        try:
            rooms = float(self.int_rooms) if self.int_rooms else 0
            rent_per_month = 870
            
            self.int_average_ratewk = round((rent_per_month * 12) / 52 / rooms if rooms else 0,2)

            average_ratefield = (rent_per_month * 12) / 52 / rooms if rooms else 0
            
            self.int_gross_rent_pa = rooms * average_ratefield * 52

            mortgage_rate = 0.075  # 6%
            # self.int_mortgage_pa = self.clean_currency(self.int_first_charge_lending or 0) * mortgage_rate
            self.int_mortgage_pa = float(f"{round(self.clean_currency(self.int_first_charge_lending or 0) * mortgage_rate):.0f}")
            
            self.int_operational_expenses_pa = 0.00
            
            self.int_management_pa = 0.00

            net_cash_flow = (
                self.int_gross_rent_pa - 
                self.int_mortgage_pa - 
                self.int_operational_expenses_pa - 
                self.int_management_pa
            )
            self.int_net_cash_flow_pa = float(f"{round(net_cash_flow):.0f}")
            
        except Exception as e:
            frappe.log_error(f"Error in rental income calculation: {str(e)}")
            # Set defaults if calculation fails
            self.int_average_ratewk = 0.00
            self.int_gross_rent_pa = 0.00
            self.int_mortgage_pa = 0.00
            self.int_operational_expenses_pa = 0.00
            self.int_management_pa = 0.00
            self.int_net_cash_flow_pa = 0.00

    def calculate_capital_growth_int(self):
        """Calculate capital growth with static 3.5% growth rate and populate child table"""
        try:
            # Clear existing table
            self.capital_growth_int_table = []
            
            if not self.int_asking_price:
                frappe.msgprint("Please enter an Asking Price to see capital growth projections")
                return
            
            current_value = self.clean_currency(self.int_asking_price)
            if current_value <= 0:
                frappe.msgprint("Please enter a valid positive Asking Price")
                return
            
            growth_rate = 0.035  # Static 3.5% growth rate
            
            # Populate child table with growth data
            for year in range(0, 11):
                increase = current_value * growth_rate
                display_value = round(current_value)
                current_value += increase
                # display_value = current_value
                display_increase = round(increase) if year < 10 else None
                # if year == 0:
                #     increase = 0
                #     display_value = current_value
                #     display_increase = 0
                # else:
                #     increase = current_value * growth_rate
                #     current_value += increase
                #     display_value = current_value
                #     display_increase = increase
                
                self.append("capital_growth_int_table", {
                    "year": year,
                    "value": "{:,.0f}".format(display_value),
                    "growth_rate": growth_rate * 100 if year < 10 else 0,
                    "increase": "{:,.0f}".format(display_increase) if display_increase is not None else None
                })
        
        except Exception as e:
            frappe.log_error(f"Error in calculate_capital_growth: {str(e)}")
            frappe.msgprint(f"Error generating capital growth table: {str(e)}")

    def calculate_capital_gain_int(self):
        """Calculate capital gain and populate child table"""
        try:
            # Clear existing table
            self.capital_gain_int_table = []
            
            if not self.int_asking_price:
                frappe.msgprint("Please enter an Asking Price to see capital gain projections")
                return
            
            current_value = self.clean_currency(self.int_asking_price)
            growth_rate = 0.035  # 3.5% growth rate
            
            # Calculate 10-year projection
            capital_value_10yr = current_value * (1 + growth_rate)**10
            mortgage_lending = self.int_first_charge_lending
            equity_investment = self.int_capital_left_in
            capital_gain = capital_value_10yr - mortgage_lending - equity_investment

            formatted_capital_value_10yr = "{:,.0f}".format(round(capital_value_10yr))
            formatted_mortgage_lending = "{:,.0f}".format(round(mortgage_lending))
            formatted_equity_investment = "{:,.0f}".format(round(equity_investment))
            formatted_capital_gain = "{:,.0f}".format(round(capital_gain))
            
            # Populate child table
            self.append("capital_gain_int_table", {
                "description": "Capital Value @ Year 10",
                "amount": formatted_capital_value_10yr
            })
            
            self.append("capital_gain_int_table", {
                "description": "Mortgage Lending",
                "amount": formatted_mortgage_lending
            })
            
            self.append("capital_gain_int_table", {
                "description": "Equity Investment Capital",
                "amount": formatted_equity_investment
            })
            
            self.append("capital_gain_int_table", {
                "description": "Capital Gain @ Year 10",
                "amount": formatted_capital_gain
            })
        
        except Exception as e:
            frappe.log_error(f"Error in calculate_capital_gain: {str(e)}")
            frappe.msgprint(f"Error generating capital gain table: {str(e)}")

    def calculate_returns_int(self):
        """Calculate investment returns metrics and populate child table"""
        try:
            # Clear existing table
            self.returns__int_table = []
            
            # Ensure we have all required values
            if None in [self.int_capital_left_in, self.int_net_cash_flow_pa, self.int_first_charge_lending, self.int_asking_price]:
                frappe.msgprint("Please complete all calculations first")
                return
                
            # Convert to floats for calculation
            retained_capital = float(self.int_capital_left_in or 0)
            annual_cashflow = float(self.int_net_cash_flow_pa or 0)
            
            # Calculate capital gain
            growth_rate = 0.035  # 3.5% growth
            current_value = self.clean_currency(self.int_asking_price or 0)
            capital_value_10yr = current_value * (1 + growth_rate)**10
            capital_gain = capital_value_10yr - float(self.int_first_charge_lending or 0) - retained_capital
            
            # Calculate returns metrics
            lifetime_cashflow = annual_cashflow * 10  # 10 years projection
            total_return = lifetime_cashflow + capital_gain
            
            # ROI Calculations
            # annualized_roi = (annual_cashflow / retained_capital) * 100 if retained_capital else 0
            # lifetime_roi = (total_return / retained_capital) * 100 if retained_capital else 0
            annualized_roi = round((annual_cashflow / retained_capital) * 100, 2) if retained_capital else 0
            # lifetime_roi = round((total_return / retained_capital) * 100, 2) if retained_capital else 0

            formatted_retained_capital = "{:,.0f}".format(round(retained_capital))
            formatted_annual_cashflow = "{:,.0f}".format(round(annual_cashflow))
            formatted_lifetime_cashflow = "{:,.0f}".format(round(lifetime_cashflow))
            formatted_capital_gain = "{:,.0f}".format(round(capital_gain))
            formatted_total_return = "{:,.0f}".format(round(total_return))
            
            # Populate child table
            self.append("returns_int_table", {
                "metric": "Retained Capital",
                "value": formatted_retained_capital,
                "percentage": 0
            })
            
            self.append("returns_int_table", {
                "metric": "Net Cash Flow PA",
                "value": formatted_annual_cashflow,
                "percentage": 0
            })
            
            self.append("returns_int_table", {
                "metric": "Total Net Lifetime Cash Flow",
                "value": formatted_lifetime_cashflow,
                "percentage": 0
            })
            
            self.append("returns_int_table", {
                "metric": "Capital Gain @ Year 10",
                "value": formatted_capital_gain,
                "percentage": 0
            })
            
            self.append("returns_int_table", {
                "metric": "Total Lifetime Return on Capital",
                "value": formatted_total_return,
                "percentage": 0
            })
            
            self.append("returns_int_table", {
                "metric": "Nett Yield",
                "value": 0,
                "percentage": annualized_roi
            })
            
            # self.append("returns_int_table", {
            #     "metric": "Lifetime Return",
            #     "value": 0,
            #     "percentage": lifetime_roi
            # })
        
        except Exception as e:
            frappe.log_error(f"Error in calculate_returns: {str(e)}")
            frappe.msgprint(f"Error calculating returns: {str(e)}")
