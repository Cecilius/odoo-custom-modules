# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    pending_categ_id = fields.Many2one('product.category', string="Pending Category")
    needs_rfb_confirmation = fields.Boolean(string="Needs RFB Confirmation", default=False)

    @api.onchange('categ_id')
    def _onchange_categ_id_rfb(self):
        if self.categ_id and self.categ_id.category_code and len(self.categ_id.category_code) == 2:
            self.pending_categ_id = self.categ_id
            self.needs_rfb_confirmation = True

    def action_confirm_rfb_category(self):
        """User clicked Confirm: Generate sequence and apply code."""
        for rec in self:
            if rec.pending_categ_id and rec.pending_categ_id.category_code:
                sequence = rec.pending_categ_id._get_or_create_sequence()
                if sequence:
                    next_seq = sequence.next_by_id()
                    rec.write({
                        'categ_id': rec.pending_categ_id.id,
                        'default_code': f"RFB-{rec.pending_categ_id.category_code}-{next_seq}",
                        'needs_rfb_confirmation': False,
                        'pending_categ_id': False,
                    })

    def action_reject_rfb_category(self):
        """User clicked Reject: Revert pending category without modifying default_code."""
        for rec in self:
            rec.write({
                'needs_rfb_confirmation': False,
                'pending_categ_id': False,
            })