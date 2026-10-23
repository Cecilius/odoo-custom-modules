"""Show template attributes through Odoo's native sale and invoice descriptions."""

from odoo import models


class SaleOrderLine(models.Model):
    """Append template attribute values to the native sale line description."""
    _inherit = 'sale.order.line'

    def _get_sale_order_line_multiline_description_variants(self):
        """Describe no-variant attributes assigned on the product template.

        Odoo only describes values selected on the sale order line itself
        (configurator picks). Template-level attribute values, such as the
        resale Condition, join them on a single line to save vertical space.
        The result is snapshotted into the invoice line name when the invoice
        is created and stays immutable afterwards.
        """
        description = super()._get_sale_order_line_multiline_description_variants()
        template = self.product_id.product_tmpl_id
        if not template:
            return description
        # Attributes picked on the line itself are described natively already.
        described_attributes = (
            self.product_no_variant_attribute_value_ids.mapped('attribute_id')
            | self.product_custom_attribute_value_ids.mapped(
                'custom_product_template_attribute_value_id.attribute_id'
            )
        )
        attribute_text = template._get_resale_attribute_description(
            exclude=described_attributes,
            company=self.order_id.company_id,
        )
        if attribute_text and attribute_text not in description:
            # Always '\n'-prefixed: the core concatenates this block directly
            # after the product name (which may itself be the only content).
            description = f'{description}\n{attribute_text}'
        return description
