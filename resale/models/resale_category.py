# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ResaleCategory(models.Model):
    _name = 'resale.category'
    _description = 'Resale Category'
    _order = 'code'

    name = fields.Char(string='Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True, size=2)
    active = fields.Boolean(string='Active', default=True)
    is_other = fields.Boolean(
        string='Other / Miscellaneous',
        help='Permanent fallback category for exceptional items.',
    )
    rfb_sequence_id = fields.Many2one(
        'ir.sequence',
        string='RFB Sequence',
        readonly=True,
        copy=False,
    )

    _code_uniq = models.Constraint(
        'unique(code)',
        'Category code must be unique.',
    )

    def _prepare_rfb_sequence_vals(self):
        self.ensure_one()
        return {
            'name': f'RFB {self.name}',
            'implementation': 'standard',
            'prefix': f'RFB-{self.code}-',
            'padding': 6,
            'number_next': 1,
            'number_increment': 1,
            'company_id': False,
        }

    def _get_or_create_rfb_sequence(self):
        self.ensure_one()
        if not self.rfb_sequence_id:
            self.rfb_sequence_id = self.env['ir.sequence'].create(
                self._prepare_rfb_sequence_vals()
            )
        return self.rfb_sequence_id

    @api.model_create_multi
    def create(self, vals_list):
        categories = super().create(vals_list)
        for category in categories:
            sequence = self.env['ir.sequence'].create(
                category._prepare_rfb_sequence_vals()
            )
            category.rfb_sequence_id = sequence.id
        return categories

    def write(self, vals):
        res = super().write(vals)
        if 'code' in vals or 'name' in vals:
            for category in self:
                if category.rfb_sequence_id:
                    update_vals = {}
                    if 'code' in vals:
                        update_vals['prefix'] = f'RFB-{category.code}-'
                    if 'name' in vals:
                        update_vals['name'] = f'RFB {category.name}'
                    if update_vals:
                        category.rfb_sequence_id.write(update_vals)
        return res

    def unlink(self):
        sequences = self.mapped('rfb_sequence_id')
        res = super().unlink()
        sequences.unlink()
        return res
