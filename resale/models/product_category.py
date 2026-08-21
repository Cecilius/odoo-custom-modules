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
    resale_protected = fields.Boolean(
        string='Protected Resale Category',
        copy=False,
        help='Protected categories cannot be deleted from the resale workflow.',
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
        if self.filtered('resale_protected'):
            from odoo.exceptions import UserError
            raise UserError('Protected resale categories cannot be deleted.')
        sequences = self.mapped('rfb_sequence_id')
        res = super().unlink()
        sequences.unlink()
        return res

    @api.model
    def _ensure_resale_category_tree(self):
        """Restore the shortcut root and standard categories if a user deleted them."""
        category_data = [
            ('product_category_computers', 'Computers', '10'),
            ('product_category_phones', 'Phones', '20'),
            ('product_category_storage', 'Storage', '30'),
            ('product_category_audio', 'Audio', '40'),
            ('product_category_gaming', 'Gaming', '50'),
            ('product_category_photo', 'Photo', '60'),
            ('product_category_network', 'Network', '70'),
            ('product_category_home', 'Home', '80'),
            ('product_category_office', 'Office', '90'),
            ('product_category_other', 'Other / Miscellaneous', '99'),
        ]
        root = self.search([('name', '=', 'Resale')], limit=1)
        if not root:
            root = self.create({
                'name': 'Resale',
                'resale_protected': True,
            })
        elif not root.resale_protected:
            root.resale_protected = True
        self._ensure_external_id('product_category_resale', root)

        for xml_name, name, prefix in category_data:
            category = self.search([('name', '=', name)], limit=1)
            if not category:
                category = self.create({
                    'name': name,
                    'parent_id': root.id,
                    'rfb_prefix': prefix,
                    'is_other': xml_name == 'product_category_other',
                })
            else:
                category.parent_id = root
                if not category.rfb_prefix:
                    category.rfb_prefix = prefix
                if xml_name == 'product_category_other':
                    category.is_other = True
            self._ensure_external_id(xml_name, category)

    def _ensure_external_id(self, name, record):
        data = self.env['ir.model.data'].sudo().search([
            ('module', '=', 'resale'),
            ('name', '=', name),
        ], limit=1)
        values = {
            'model': 'product.category',
            'res_id': record.id,
            'noupdate': True,
        }
        if data:
            data.write(values)
        else:
            self.env['ir.model.data'].sudo().create(dict(
                values,
                module='resale',
                name=name,
            ))
