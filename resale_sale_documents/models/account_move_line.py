"""Show template attributes on invoice lines created without a sale order."""

from odoo import models


class AccountMoveLine(models.Model):
    """Describe product attributes in the native invoice line name."""
    _inherit = 'account.move.line'

    def _compute_name(self):
        """Append attribute rows after the standard product name build-up.

        Covers hand-made invoices: the core compute renders the product name
        and sale description when a product is picked, and the attribute text
        joins it on one further line. Lines coming from sale orders keep the
        name written by the invoicing flow, whose identical row is then not
        duplicated.
        """
        super()._compute_name()
        for line in self:
            if (
                not line.name
                or not line.product_id
                or line.display_type not in (False, 'product')
                or line.move_id.inalterable_hash
                or not line.move_id.is_invoice(include_receipts=True)
                or line.move_id.move_type not in ('out_invoice', 'out_refund')
            ):
                continue
            template = line.product_id.product_tmpl_id
            lang = line.move_id.partner_id.lang or line.partner_id.lang
            if lang:
                template = template.with_context(lang=lang)
            attribute_text = template._get_resale_attribute_description(
                company=line.move_id.company_id
            )
            if attribute_text and attribute_text not in line.name:
                line.name = f'{line.name}\n{attribute_text}'
