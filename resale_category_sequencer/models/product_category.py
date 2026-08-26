# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductCategory(models.Model):
    _inherit = 'product.category'

    category_code = fields.Char(
        string="Category Code (2-Digit)",
        size=2,
        help="2-digit category code (00-99) used for generating internal references."
    )

    _sql_constraints = [
        (
            'category_code_uniq',
            'unique(category_code)',
            'The Category Code must be unique across all categories!'
        )
    ]

    @api.constrains('category_code')
    def _check_category_code(self):
        for rec in self:
            if rec.category_code:
                if not rec.category_code.isdigit() or len(rec.category_code) != 2:
                    raise ValidationError(
                        _("Category Code must be exactly 2 numeric digits (00-99).")
                    )

    def _get_or_create_sequence(self):
        self.ensure_one()
        if not self.category_code:
            return None

        seq_code = f"product.category.seq.{self.category_code}"
        sequence = self.env['ir.sequence'].sudo().search([('code', '=', seq_code)], limit=1)

        if not sequence:
            sequence = self.env['ir.sequence'].sudo().create({
                'name': f"Product Sequence - Category {self.category_code} ({self.name})",
                'code': seq_code,
                'prefix': '',
                'padding': 5,
                'number_increment': 1,
                'number_next': 1,
                'implementation': 'standard',
            })
        return sequence