"""Build the attribute description line used on sale and invoice documents."""

from odoo import models


class ProductTemplate(models.Model):
    """Expose the no-variant attribute summary consumed by line description hooks."""
    _inherit = 'product.template'

    def _get_resale_attribute_description(self, exclude=None, company=None):
        """Return one line describing the attributes shown on document lines.

        Includes only non-variant attribute lines flagged 'Show on sale &
        invoice lines' (variant values are already in the product display
        name), and prepends the company's second-hand marker text when the
        product's condition maps to a second-hand item. Names render in the
        language of the recordset's context.
        """
        self.ensure_one()
        exclude = exclude or self.env['product.attribute']
        company = (company or self.env.company).with_context(self.env.context)
        segments = []
        marker = (company.second_hand_text or '').strip()
        if (
            marker
            and self.condition_value_id
            and self.condition_text_id.is_second_hand
        ):
            segments.append(marker)
        for attribute_line in self.attribute_line_ids.filtered(
            lambda item:
                item.attribute_id.create_variant == 'no_variant'
                and item.value_ids
                and item.attribute_id.resale_show_on_lines
                and item.attribute_id not in exclude
        ):
            values = ', '.join(attribute_line.value_ids.mapped('name'))
            segments.append(f'{attribute_line.attribute_id.name}: {values}')
        return ', '.join(segments)
