# -*- coding: utf-8 -*-
"""Category-code validation and RFB sequence management."""
import re

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


_RFB_REFERENCE = re.compile(r'^RFB-(?P<category>\d{2})-(?P<number>\d+)$')


class ProductCategory(models.Model):
    _inherit = 'product.category'

    category_code = fields.Char(
        string="Category Code (2-Digit)",
        size=2,
        index=False,
        help="2-digit category code (00-99) used for generating internal references."
    )

    _category_code_unique = models.Constraint(
        'unique(category_code)',
        'The Category Code must be unique across all categories!',
    )

    @api.constrains('category_code')
    def _check_category_code(self):
        """Ensure assigned category codes are exactly two decimal digits."""
        for rec in self:
            if rec.category_code:
                if not rec.category_code.isdigit() or len(rec.category_code) != 2:
                    raise ValidationError(
                        _("Category Code must be exactly 2 numeric digits (00-99).")
                    )

    def copy(self, default=None):
        """Duplicate a category without copying its globally unique code."""
        default = dict(default or {})
        default.setdefault('category_code', False)
        return super().copy(default)

    def _get_or_create_sequence(self):
        """Return the sequence associated with this category's code."""
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

    def _adjust_rfb_sequences(self, dry_run=True):
        """Align category sequences with existing RFB product references.

        References are matched by their embedded category code, even if a
        product was later moved to another category. Sequences only advance.

        :param bool dry_run: report intended changes without writing anything.
        :return: one result dictionary per coded category.
        """
        highest = {}
        products = self.env['product.template'].search([
            ('default_code', 'ilike', 'RFB-%'),
        ])
        for product in products:
            match = _RFB_REFERENCE.match(
                (product.default_code or '').strip().upper()
            )
            if match:
                code = match.group('category')
                highest[code] = max(
                    highest.get(code, 0), int(match.group('number'))
                )

        # Contextual server actions pass the selected categories in ``self``.
        # An empty model recordset, as used by the shell script, intentionally
        # means all coded categories.
        categories = self.sudo() if self else self.env['product.category'].sudo().search(
            [('category_code', '!=', False)],
            order='category_code,id',
        )
        sequences = self.env['ir.sequence'].sudo()
        results = []
        for category in categories:
            code = category.category_code
            sequence_code = f'product.category.seq.{code}'
            sequence = sequences.search([('code', '=', sequence_code)], limit=1)
            missing = not sequence
            current_next = sequence.number_next if sequence else 1
            target_next = max(current_next, highest.get(code, 0) + 1)
            changed = missing or target_next != current_next

            if changed and not dry_run:
                sequence = category._get_or_create_sequence()
                if sequence.number_next != target_next:
                    sequence.write({'number_next': target_next})

            results.append({
                'category_id': category.id,
                'category': category.display_name,
                'category_code': code,
                'sequence_code': sequence_code,
                'existing_highest': highest.get(code, 0),
                'current_next': current_next,
                'target_next': target_next,
                'changed': changed,
            })
        return results
