from odoo import api, fields, models, Command


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    _ATTRIBUTE_KEYS = ('brand', 'condition', 'box', 'warranty')

    def _get_mapped_attribute(self, key):
        configured_id = self.env['ir.config_parameter'].sudo().get_param(
            f'resale_attributes.{key}_attribute_id'
        )
        attribute_model = self.env['product.attribute']
        attribute = (
            attribute_model.browse(int(configured_id)).exists()
            if configured_id and configured_id.isdigit()
            else attribute_model
        )
        return attribute or self.env.ref(
            f'resale_attributes.product_attribute_{key}',
            raise_if_not_found=False,
        )

    brand_attribute_id = fields.Many2one(
        'product.attribute', string='Brand Attribute',
        compute='_compute_brand_attribute_id',
    )
    condition_attribute_id = fields.Many2one(
        'product.attribute', string='Condition Attribute',
        compute='_compute_condition_attribute_id',
    )
    box_attribute_id = fields.Many2one(
        'product.attribute', string='Box Attribute',
        compute='_compute_box_attribute_id',
    )
    warranty_attribute_id = fields.Many2one(
        'product.attribute', string='Warranty Attribute',
        compute='_compute_warranty_attribute_id',
    )

    brand_value_id = fields.Many2one(
        'product.attribute.value', string='Brand',
        compute='_compute_brand_value_id', inverse='_inverse_brand_value_id',
    )
    condition_value_id = fields.Many2one(
        'product.attribute.value', string='Condition',
        compute='_compute_condition_value_id', inverse='_inverse_condition_value_id',
    )
    condition_text_id = fields.Many2one(
        'resale.condition.text',
        string='Condition Text Mapping',
        compute='_compute_condition_text_id',
        store=True,
        index=True,
    )
    condition_operator_text = fields.Text(
        related='condition_text_id.operator_text',
        string='Operator Text',
        readonly=True,
        store=True,
    )
    condition_listing_text = fields.Html(
        related='condition_text_id.listing_text',
        string='Listing Text',
        readonly=True,
        store=True,
    )
    condition_followup_text = fields.Text(
        related='condition_text_id.followup_text',
        string='Follow-up Text',
        readonly=True,
        store=True,
    )
    box_value_id = fields.Many2one(
        'product.attribute.value', string='Box',
        compute='_compute_box_value_id', inverse='_inverse_box_value_id',
    )
    warranty_value_id = fields.Many2one(
        'product.attribute.value', string='Warranty',
        compute='_compute_warranty_value_id', inverse='_inverse_warranty_value_id',
    )

    @api.depends('attribute_line_ids.value_ids')
    def _compute_brand_attribute_id(self):
        self._compute_mapped_attribute_id('brand')

    @api.depends('attribute_line_ids.value_ids')
    def _compute_condition_attribute_id(self):
        self._compute_mapped_attribute_id('condition')

    @api.depends('attribute_line_ids.value_ids')
    def _compute_box_attribute_id(self):
        self._compute_mapped_attribute_id('box')

    @api.depends('attribute_line_ids.value_ids')
    def _compute_warranty_attribute_id(self):
        self._compute_mapped_attribute_id('warranty')

    def _compute_mapped_attribute_id(self, key):
        attribute = self._get_mapped_attribute(key)
        for template in self:
            setattr(template, f'{key}_attribute_id', attribute)

    def _compute_brand_value_id(self):
        self._compute_mapped_value('brand')

    def _compute_condition_value_id(self):
        self._compute_mapped_value('condition')

    def _compute_box_value_id(self):
        self._compute_mapped_value('box')

    def _compute_warranty_value_id(self):
        self._compute_mapped_value('warranty')

    @api.depends('condition_value_id')
    def _compute_condition_text_id(self):
        Mapping = self.env['resale.condition.text']
        for template in self:
            template.condition_text_id = Mapping.search([
                ('condition_value_id', '=', template.condition_value_id.id),
                ('active', '=', True),
            ], limit=1)

    def _compute_mapped_value(self, key):
        for template in self:
            attribute = template._get_mapped_attribute(key)
            line = template.attribute_line_ids.filtered(
                lambda item: attribute and item.attribute_id == attribute
            )[:1]
            setattr(template, f'{key}_value_id', line.value_ids[:1] if line else False)

    def _inverse_brand_value_id(self):
        self._inverse_mapped_value('brand')

    def _inverse_condition_value_id(self):
        self._inverse_mapped_value('condition')

    def _inverse_box_value_id(self):
        self._inverse_mapped_value('box')

    def _inverse_warranty_value_id(self):
        self._inverse_mapped_value('warranty')

    def _inverse_mapped_value(self, key):
        attribute = self._get_mapped_attribute(key)
        if not attribute:
            return
        for template in self:
            value = getattr(template, f'{key}_value_id')
            if value and value.attribute_id != attribute:
                continue
            line = template.attribute_line_ids.filtered(
                lambda item: item.attribute_id == attribute
            )[:1]
            if value:
                if line:
                    line.value_ids = [Command.set([value.id])]
                else:
                    self.env['product.template.attribute.line'].create({
                        'product_tmpl_id': template.id,
                        'attribute_id': attribute.id,
                        'value_ids': [Command.link(value.id)],
                    })
            elif line:
                line.unlink()
