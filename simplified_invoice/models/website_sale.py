from odoo import _
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request


class WebsiteSaleExtended(WebsiteSale):
    def _website_order_requires_tax_id(self, order, values):
        partner = order.partner_id.commercial_partner_id
        country_code = values.get('country_code') or partner.country_id.code
        vat = values.get('vat') or partner.vat
        company_name = values.get('company_name') or values.get('company')
        is_spain = country_code == 'ES'
        is_b2b = bool(vat) or bool(company_name) or partner.company_type == 'company' or partner.invoice_identification_type == 'full'
        if is_spain and not is_b2b and order.amount_total <= 400.0:
            return False
        if is_spain and order.amount_total > 400.0:
            return True
        if is_b2b:
            return True
        return False

    def _get_mandatory_billing_fields(self):
        fields = super()._get_mandatory_billing_fields()
        order = request.website.sale_get_order()
        if order and order.amount_total > 400.0 and order.partner_id.country_id.code == 'ES' and 'vat' not in fields:
            fields.append('vat')
        return fields

    def _checkout_form_validate(self, mode, all_form_values, data):
        error, error_message = super()._checkout_form_validate(mode, all_form_values, data)
        order = request.website.sale_get_order()
        if order and self._website_order_requires_tax_id(order, all_form_values) and not all_form_values.get('vat'):
            error['vat'] = 'missing'
            error_message.append(_('Tax ID (NIF/NIE/VAT) is required for this invoice.'))
        return error, error_message
