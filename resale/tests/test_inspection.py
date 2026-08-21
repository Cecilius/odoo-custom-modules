# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestResaleInspection(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True, resale_item=True))
        cls.category = cls.env['product.category'].create({
            'name': 'Test Category',
            'rfb_prefix': 'TC',
        })
        cls.condition = cls.env['resale.condition'].create({
            'name': 'Test Condition',
            'code': 'TCO',
            'condition_factor': 0.9,
        })

    def test_detailed_test_updates_item(self):
        product = self.env['product.product'].create({
            'name': 'Detailed Test Item',
            'categ_id': self.category.id,
        })
        test = self.env['resale.detailed.test'].create({
            'product_id': product.id,
            'result': 'pass',
            'final_condition_id': self.condition.id,
            'final_functional_status': 'working',
            'final_disposition': 'pricing',
        })
        test.action_complete()
        self.assertEqual(test.state, 'done')
        self.assertEqual(product.resale_state, 'ready')
        self.assertEqual(product.condition_id, self.condition)
        self.assertEqual(product.functional_status, 'working')

