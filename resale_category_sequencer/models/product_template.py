# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    has_category_code = fields.Boolean(
        compute='_compute_has_category_code',
        string="Has Category Code"
    )

    @api.depends('categ_id', 'categ_id.category_code')
    def _compute_has_category_code(self):
        for rec in self:
            rec.has_category_code = bool(
                rec.categ_id and rec.categ_id.category_code and len(rec.categ_id.category_code) == 2
            )

    def action_generate_rfb_code(self):
        """Triggered by the Generate RFB Code button."""
        self.ensure_one()
        
        # If default_code already exists, open confirmation dialog wizard
        if self.default_code:
            return {
                'name': _('Overwrite Internal Reference?'),
                'type': 'ir.actions.act_window',
                'res_model': 'product.rfb.overwrite.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_product_id': self.id,
                    'default_existing_code': self.default_code,
                }
            }
        
        # Otherwise generate directly
        self._generate_and_assign_rfb_code()

    def _generate_and_assign_rfb_code(self):
        self.ensure_one()
        if self.categ_id and self.categ_id.category_code:
            sequence = self.categ_id._get_or_create_sequence()
            if sequence:
                next_seq = sequence.next_by_id()
                self.default_code = f"RFB-{self.categ_id.category_code}-{next_seq}"