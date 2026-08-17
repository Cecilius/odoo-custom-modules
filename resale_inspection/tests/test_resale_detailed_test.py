# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestResaleDetailedTest(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.category = cls.env['resale.category'].create({
            'name': 'Test Category',
            'code': 'TC',
        })
        cls.item = cls.env['resale.item'].create({
            'rfb': 'RFB-TC-000101',
            'category_id': cls.category.id,
            'state': 'detailed_test',
        })
        cls.condition = cls.env['resale.condition'].create({
            'name': 'Test Condition',
            'code': 'TCO',
        })

    def test_detailed_test_complete_moves_item_state(self):
        test = self.env['resale.detailed.test'].create({
            'item_id': self.item.id,
            'result': 'pass',
            'final_condition_id': self.condition.id,
            'final_functional_status': 'working',
            'final_disposition': 'pricing',
        })
        self.assertEqual(test.state, 'draft')
        test.action_complete()
        self.assertEqual(test.state, 'done')
        self.assertEqual(self.item.state, 'pricing')
        self.assertEqual(self.item.condition_id, self.condition)

    def test_detailed_test_disposition_scrap(self):
        test = self.env['resale.detailed.test'].create({
            'item_id': self.item.id,
            'result': 'fault',
            'final_functional_status': 'not_working',
            'final_disposition': 'scrap',
        })
        test.action_complete()
        self.assertEqual(self.item.state, 'scrapped')
