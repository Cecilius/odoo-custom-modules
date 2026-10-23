"""Condition attribute mappings used in operator and listing text."""

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResaleConditionText(models.Model):
    """Map one configured condition value to operator and listing wording."""
    _name = 'resale.condition.text'
    _description = 'Condition Text Mapping'
    _order = 'condition_value_id'

    condition_attribute_id = fields.Many2one(
        'product.attribute',
        string='Condition Attribute',
        compute='_compute_condition_attribute_id',
    )
    condition_value_id = fields.Many2one(
        'product.attribute.value',
        string='Condition',
        required=True,
        ondelete='cascade',
    )
    operator_text = fields.Text(string='Operator Text', translate=True)
    listing_text = fields.Text(string='Listing Text', translate=True)
    followup_text = fields.Text(string='Invoice Text', translate=True)
    active = fields.Boolean(default=True)

    _condition_value_unique = models.Constraint(
        'unique(condition_value_id)',
        'Each condition value can have only one text mapping.',
    )

    @api.depends()
    def _compute_condition_attribute_id(self):
        """Resolve the configured Condition attribute, with an XML-ID fallback."""
        configured_id = self.env['ir.config_parameter'].sudo().get_param(
            'resale_attributes.condition_attribute_id'
        )
        attribute_model = self.env['product.attribute']
        attribute = (
            attribute_model.browse(int(configured_id)).exists()
            if configured_id and configured_id.isdigit()
            else attribute_model
        )
        for mapping in self:
            mapping.condition_attribute_id = attribute or self.env.ref(
                'resale_attributes.product_attribute_condition',
                raise_if_not_found=False,
            )

    @api.constrains('condition_value_id')
    def _check_condition_value_attribute(self):
        """Prevent mappings from using values of another product attribute."""
        for mapping in self:
            if (
                mapping.condition_value_id
                and mapping.condition_attribute_id
                and mapping.condition_value_id.attribute_id != mapping.condition_attribute_id
            ):
                raise ValidationError(
                    'The selected value must belong to the configured Condition attribute.'
                )
