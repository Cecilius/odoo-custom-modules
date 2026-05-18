from odoo.http import request
from odoo.addons.account.controllers.portal import PortalAccount

class SimplifiedInvoicePortalAccount(PortalAccount):
    def _get_mandatory_billing_address_fields(self, country_sudo):
        field_names = super()._get_mandatory_billing_address_fields(country_sudo)

        if request.env.company.country_code == country_sudo.code == 'ES':
            order = request.website.sale_get_order()
            amount_total = order.amount_total if order else 0.0
            partner = order.partner_id.commercial_partner_id if order and order.partner_id else request.env['res.partner']

            is_b2b = bool(partner.vat) or partner.company_type == 'company'

            if not is_b2b and amount_total <= 400.0:
                field_names.discard('vat')

        return field_names