from odoo.http import request
from odoo.addons.account.controllers.portal import PortalAccount


class SimplifiedInvoicePortalAccount(PortalAccount):
    def _get_mandatory_billing_address_fields(self, country_sudo):
        field_names = super()._get_mandatory_billing_address_fields(country_sudo)

        if request.env.company.country_code == country_sudo.code == 'ES':
            order_id = request.session.get('sale_order_id')
            order = request.env['sale.order'].sudo().browse(order_id) if order_id else request.env['sale.order']
            amount_total = order.amount_total if order and order.exists() else 0.0

            if amount_total <= 400.0:
                field_names.discard('vat')

        return field_names