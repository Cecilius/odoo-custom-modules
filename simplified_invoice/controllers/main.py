from odoo.addons.account.controllers.portal import PortalAccount
from odoo.http import request


class SimplifiedInvoicePortalAccount(PortalAccount):
    def _get_mandatory_billing_address_fields(self, country_sudo):
        """Require VAT/NIF for Spanish customers in billing addresses on Spanish e-commerce."""
        field_names = super()._get_mandatory_billing_address_fields(country_sudo)

        if request.env.company.country_code == country_sudo.code == 'ES':
            field_names.discard('vat')

        return field_names