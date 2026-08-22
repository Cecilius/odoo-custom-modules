# -*- coding: utf-8 -*-
from odoo import models, fields, _


class ProductRfbOverwriteWizard(models.TransientModel):
    _name = 'product.rfb.overwrite.wizard'
    _description = 'Confirm Internal Reference Overwrite'

    product_id = fields.Many2one('product.template', required=True)
    existing_code = fields.Char(string="Current Internal Reference", readonly=True)

    def action_confirm_overwrite(self):
        self.ensure_one()
        self.product_id._generate_and_assign_rfb_code()