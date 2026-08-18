# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestResaleProduct(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.category = cls.env['resale.category'].create({
            'name': 'Test Category',
            'code': 'TC',
        })
        cls.brand = cls.env['resale.brand'].create({'name': 'TestBrand'})
        cls.manager = cls.env['res.users'].create({
            'name': 'Resale Manager',
            'login': 'resale_manager',
            'group_ids': [(6, 0, [cls.env.ref('resale.group_resale_manager').id])],
        })

    def test_create_product_generates_rfb(self):
        product = self.env['product.product'].create({
            'name': 'Test Item',
            'resale_category_id': self.category.id,
        })
        self.assertTrue(product.rfb)
        self.assertTrue(product.rfb.startswith('RFB-TC-'))
        self.assertEqual(product.default_code, product.rfb)
        self.assertEqual(product.barcode, product.rfb)
        self.assertEqual(product.type, 'consu')
        self.assertTrue(product.is_storable)

    def test_rfb_sequence_increments(self):
        p1 = self.env['product.product'].create({
            'name': 'Sequence Item 1',
            'resale_category_id': self.category.id,
        })
        p2 = self.env['product.product'].create({
            'name': 'Sequence Item 2',
            'resale_category_id': self.category.id,
        })
        self.assertTrue(p2.rfb > p1.rfb)

    def test_rfb_unique(self):
        self.env['product.product'].create({
            'name': 'RFB Item 1',
            'rfb': 'RFB-TC-999999',
            'resale_category_id': self.category.id,
        })
        with self.assertRaises(ValidationError):
            self.env['product.product'].create({
                'name': 'RFB Item 1 Duplicate',
                'rfb': 'RFB-TC-999999',
                'resale_category_id': self.category.id,
            })

    def test_complete_evaluation(self):
        product = self.env['product.product'].create({
            'name': 'Eval Item',
            'resale_category_id': self.category.id,
        })
        product.write({
            'eval_basic_result': 'pass',
            'eval_disposition': 'test',
        })
        product.action_complete_evaluation()
        self.assertTrue(product.eval_done)
        self.assertEqual(product.resale_state, 'inspecting')
        self.assertEqual(product.eval_user_id, self.env.user)

    def test_complete_evaluation_requires_result(self):
        product = self.env['product.product'].create({
            'name': 'Eval Item No Result',
            'resale_category_id': self.category.id,
        })
        with self.assertRaises(UserError):
            product.action_complete_evaluation()

    def test_lock_cost_only_manager(self):
        product = self.env['product.product'].create({
            'name': 'Lock Item',
            'resale_category_id': self.category.id,
        })
        product.with_user(self.manager)._lock_cost()
        self.assertEqual(product.cost_status, 'locked')
