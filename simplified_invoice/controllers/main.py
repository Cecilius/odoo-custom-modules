from odoo.http import request

from odoo.addons.account.controllers.portal import PortalAccount


class SimplifiedInvoicePortalAccount(PortalAccount):
    def _get_mandatory_billing_address_fields(self, country_sudo):
        """Only require a VAT/NIF at checkout when a full invoice will be needed.

        Mirrors ``account.move._check_simplified_invoice_rules``: a full invoice
        is required above the company's simplified-invoice limit or for
        company-type (B2B) customers.
        """
        field_names = super()._get_mandatory_billing_address_fields(country_sudo)
        company = request.env.company
        if not (company.country_code == country_sudo.code == "ES"):
            return field_names

        # The cart belongs to the current session; sudo only reads its total and partner.
        order_id = request.session.get("sale_order_id")
        order = request.env["sale.order"].sudo().browse(order_id).exists() if order_id else None
        amount_total = order.amount_total if order else 0.0
        currency = order.currency_id if order else company.currency_id
        over_limit = currency.compare_amounts(amount_total, company.l10n_es_simplified_invoice_limit) > 0
        is_b2b = bool(order and order.partner_id.commercial_partner_id.is_company)

        if not (over_limit or is_b2b):
            field_names.discard("vat")
        return field_names
