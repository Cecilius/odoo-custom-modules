from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleSpanishCheckoutOverride(WebsiteSale):
    def _get_mandatory_billing_address_fields(self, country_sudo):
        field_names = super()._get_mandatory_billing_address_fields(country_sudo)

        if 'vat' in field_names and request.env.company.country_code == country_sudo.code == 'ES':
            order = request.website.sale_get_order()
            amount_total = order.amount_total if order else 0.0
            partner = order.partner_id.commercial_partner_id if order and order.partner_id else request.env['res.partner']

            is_b2b = bool(getattr(partner, 'vat', False)) or getattr(partner, 'company_type', False) == 'company'

            vat_required = False
            if amount_total > 400.0:
                vat_required = True
            elif is_b2b:
                vat_required = True

            if not vat_required:
                field_names.discard('vat')

        return field_names