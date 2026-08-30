from psycopg2 import IntegrityError
from odoo.tests.common import TransactionCase


class TestProductCategory(TransactionCase):

    def test_category_code_must_be_unique(self):
        used_codes = set(self.env['product.category'].search([
            ('category_code', '!=', False),
        ]).mapped('category_code'))
        category_code = next(
            '%02d' % number
            for number in range(100)
            if '%02d' % number not in used_codes
        )
        self.env['product.category'].create({
            'name': 'Unique category A',
            'category_code': category_code,
        })
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self.env['product.category'].create({
                    'name': 'Unique category B',
                    'category_code': category_code,
                })

    def test_copy_clears_category_code(self):
        used_codes = set(self.env['product.category'].search([
            ('category_code', '!=', False),
        ]).mapped('category_code'))
        category_code = next(
            '%02d' % number
            for number in range(100)
            if '%02d' % number not in used_codes
        )
        category = self.env['product.category'].create({
            'name': 'Category to copy',
            'category_code': category_code,
        })

        copied_category = category.copy()

        self.assertFalse(copied_category.category_code)
