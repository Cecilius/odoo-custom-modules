# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('categ_id'):
                self._assign_rfb_sequence(vals)
        return super().create(vals_list)

    def write(self, vals):
        if 'categ_id' in vals:
            self._assign_rfb_sequence(vals)
        return super().write(vals)

    def _assign_rfb_sequence(self, vals):
        """Assigns default_code in format RFB-XX-YYYYYY based on category sequence."""
        category_id = vals.get('categ_id')
        if not category_id:
            return

        category = self.env['product.category'].browse(category_id)
        if category.category_code and len(category.category_code) == 2:
            sequence = category._get_or_create_sequence()
            if sequence:
                next_seq = sequence.next_by_id()
                vals['default_code'] = f"RFB-{category.category_code}-{next_seq}"
