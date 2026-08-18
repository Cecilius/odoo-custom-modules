# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ProductCategory(models.Model):
    _inherit = 'product.category'

    rfb_prefix = fields.Char(
        string='RFB Prefix',
        size=2,
        help='Two-digit prefix used to build RFB codes (e.g. 99 for Other).',
    )
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

    _rfb_prefix_uniq = models.Constraint(
        'unique(rfb_prefix)',
        'RFB prefix must be unique.',
    )

    def _prepare_rfb_sequence_vals(self):
        self.ensure_one()
        return {
            'name': f'RFB {self.name}',
            'implementation': 'standard',
            'prefix': f'RFB-{self.rfb_prefix}-',
            'padding': 6,
            'number_next': 1,
            'number_increment': 1,
            'company_id': False,
        }

    def _get_or_create_rfb_sequence(self):
        self.ensure_one()
        if not self.rfb_prefix:
            return self.env['ir.sequence']
        if not self.rfb_sequence_id:
            self.rfb_sequence_id = self.env['ir.sequence'].create(
                self._prepare_rfb_sequence_vals()
            )
        return self.rfb_sequence_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'rfb_prefix' in vals:
                vals['rfb_prefix'] = (vals.get('rfb_prefix') or '').strip() or False
        categories = super().create(vals_list)
        for category in categories:
            if category.rfb_prefix and not category.rfb_sequence_id:
                sequence = self.env['ir.sequence'].create(
                    category._prepare_rfb_sequence_vals()
                )
                category.rfb_sequence_id = sequence.id
        return categories

    def write(self, vals):
        if 'rfb_prefix' in vals:
            vals['rfb_prefix'] = (vals.get('rfb_prefix') or '').strip() or False
        res = super().write(vals)
        if 'rfb_prefix' in vals or 'name' in vals:
            for category in self:
                if not category.rfb_sequence_id:
                    continue
                update_vals = {}
                if 'rfb_prefix' in vals:
                    if category.rfb_prefix:
                        update_vals['prefix'] = f'RFB-{category.rfb_prefix}-'
                    else:
                        # Prefix removed: keep existing sequence name but do not update prefix
                        pass
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
