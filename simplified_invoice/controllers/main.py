from odoo.addons.account.controllers.portal import PortalAccount
from odoo.http import request


class SimplifiedInvoicePortalAccount(PortalAccount):
    def _get_mandatory_billing_address_fields(self, country_sudo):

        # Reuse the Spanish localization limit from the current company to keep checkout logic aligned with invoices.
        if request.env.company.country_code == country_sudo.code == "ES":
            order_id = request.session.get("sale_order_id")
            order = request.env["sale.order"].sudo().browse(order_id) if order_id else request.env["sale.order"]
            amount_total = order.amount_total if order and order.exists() else 0.0
            limit = request.env.company.l10n_es_simplified_invoice_limit or 0.0
            partner = order.partner_id.commercial_partner_id if order and order.partner_id else request.env['res.partner']
            is_b2b = bool(getattr(partner, 'vat', False)) or getattr(partner, 'company_type', False) == 'company'

            vat_required = False
            if amount_total >= limit:
                vat_required = True
            elif is_b2b:
                vat_required = True

            if not vat_required:
                field_names.discard('vat')

        return field_names