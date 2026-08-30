from psycopg2 import IntegrityError
from odoo.tests.common import TransactionCase


class TestProductTemplate(TransactionCase):
    """Verify that populated product references cannot be reused."""

    def test_default_code_must_be_unique(self):
        used_codes = set(self.env['product.template'].search([
            ('default_code', '!=', False),
        ]).mapped('default_code'))
        default_code = next(
            'TEST-DEFAULT-CODE-%d' % number
            for number in range(10000)
            if 'TEST-DEFAULT-CODE-%d' % number not in used_codes
        )
        self.env['product.template'].create({
            'name': 'Unique product A',
            'default_code': default_code,
        })
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self.env['product.template'].create({
                    'name': 'Unique product B',
                    'default_code': default_code.lower(),
                })
