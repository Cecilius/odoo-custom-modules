from odoo import api, fields, models


class ResaleCategoryMapping(models.Model):
    _name = 'resale.category.mapping'
    _description = 'Resale Category Mapping'
    _order = 'rfb_code, category_id'

    category_id = fields.Many2one(
        'product.category',
        string='Product Category',
        required=True,
        ondelete='restrict',
    )
    rfb_code = fields.Char(string='RFB Code', required=True, size=2)
    sequence_id = fields.Many2one(
        'ir.sequence', string='RFB Sequence', readonly=True, copy=False,
    )
    active = fields.Boolean(default=True)
    name = fields.Char(related='category_id.complete_name', string='Category', readonly=True)

    _category_unique = models.Constraint(
        'unique(category_id)',
        'Each product category can have only one resale RFB mapping.',
    )
    _code_unique = models.Constraint(
        'unique(rfb_code)',
        'Each resale RFB code must be unique.',
    )

    def _prepare_sequence_vals(self):
        self.ensure_one()
        return {
            'name': f'RFB {self.category_id.complete_name}',
            'prefix': f'RFB-{self.rfb_code}-',
            'padding': 6,
            'number_next': 1,
            'number_increment': 1,
            'company_id': False,
        }

    @api.model_create_multi
    def create(self, vals_list):
        mappings = super().create(vals_list)
        for mapping in mappings:
            if not mapping.sequence_id:
                mapping.sequence_id = self.env['ir.sequence'].create(
                    mapping._prepare_sequence_vals()
                )
        return mappings

    def write(self, vals):
        if 'rfb_code' in vals:
            vals['rfb_code'] = (vals.get('rfb_code') or '').strip()
        result = super().write(vals)
        if {'rfb_code', 'category_id'}.intersection(vals):
            for mapping in self:
                if mapping.sequence_id:
                    mapping.sequence_id.write({
                        'name': f'RFB {mapping.category_id.complete_name}',
                        'prefix': f'RFB-{mapping.rfb_code}-',
                    })
        return result

    def _synchronize_sequence(self):
        for mapping in self.filtered(lambda item: item.sequence_id):
            prefix = f'RFB-{mapping.rfb_code}-'
            max_number = 0
            products = self.env['product.product'].search([
                ('rfb', '=like', f'{prefix}%'),
            ])
            for product in products:
                try:
                    max_number = max(max_number, int(product.rfb[len(prefix):]))
                except (TypeError, ValueError):
                    continue
            if mapping.sequence_id.number_next <= max_number:
                mapping.sequence_id.number_next = max_number + 1

    @api.model
    def _migrate_from_product_categories(self):
        for category in self.env['product.category'].search([
            ('rfb_prefix', '!=', False),
        ]):
            mapping = self.search([('category_id', '=', category.id)], limit=1)
            if not mapping:
                mapping = self.create({
                    'category_id': category.id,
                    'rfb_code': category.rfb_prefix,
                })
            if category.rfb_sequence_id and mapping.sequence_id != category.rfb_sequence_id:
                mapping.sequence_id = category.rfb_sequence_id
            mapping._synchronize_sequence()

    @api.model
    def get_for_category(self, category):
        return self.search([
            ('category_id', '=', category.id),
            ('active', '=', True),
        ], limit=1)
