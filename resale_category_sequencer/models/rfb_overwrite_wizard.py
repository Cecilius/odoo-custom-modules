# -*- coding: utf-8 -*-
"""Confirmation wizard for replacing an existing RFB product reference."""
from odoo import models, fields, _


class ProductRfbOverwriteWizard(models.TransientModel):
    """Require explicit confirmation before consuming a new RFB sequence value."""
    _name = 'product.rfb.overwrite.wizard'
    _description = 'Confirm Internal Reference Overwrite'

    product_id = fields.Many2one('product.template', required=True)
    existing_code = fields.Char(string="Current Internal Reference", readonly=True)

    def action_confirm_overwrite(self):
        """Generate and assign the replacement reference after confirmation."""
        self.ensure_one()
        self.product_id._generate_and_assign_rfb_code()
