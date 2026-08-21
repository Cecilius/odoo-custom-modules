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
        cls.category = cls.env['product.category'].create({
            'name': 'Test Category',
            'rfb_prefix': 'TC',
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
            'categ_id': self.category.id,
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
            'categ_id': self.category.id,
        })
        p2 = self.env['product.product'].create({
            'name': 'Sequence Item 2',
            'categ_id': self.category.id,
        })
        self.assertTrue(p2.rfb > p1.rfb)

    def test_rfb_sequence_skips_existing_numbers(self):
        self.env['product.product'].create({
            'name': 'Existing RFB Item',
            'categ_id': self.category.id,
            'rfb': 'RFB-TC-000001',
        })
        self.category.rfb_sequence_id.number_next = 1
        product = self.env['product.product'].create({
            'name': 'Next RFB Item',
            'categ_id': self.category.id,
        })
        self.assertEqual(product.rfb, 'RFB-TC-000002')

    def test_rfb_unique(self):
        self.env['product.product'].create({
            'name': 'RFB Item 1',
            'rfb': 'RFB-TC-999999',
            'categ_id': self.category.id,
        })
        with self.assertRaises(ValidationError):
            self.env['product.product'].create({
                'name': 'RFB Item 1 Duplicate',
                'rfb': 'RFB-TC-999999',
                'categ_id': self.category.id,
            })

    def test_complete_evaluation(self):
        product = self.env['product.product'].create({
            'name': 'Eval Item',
            'categ_id': self.category.id,
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
            'categ_id': self.category.id,
        })
        with self.assertRaises(UserError):
            product.action_complete_evaluation()

    def test_lock_cost_only_manager(self):
        product = self.env['product.product'].create({
            'name': 'Lock Item',
            'categ_id': self.category.id,
        })
        product.with_user(self.manager)._lock_cost()
        self.assertEqual(product.cost_status, 'locked')

    def test_goods_default_to_new_grade_and_warranty(self):
        product = self.env['product.product'].create({'name': 'New Goods'})
        self.assertEqual(product.condition_grade_value_id.name, 'New')
        self.assertEqual(product.warranty_policy_id.duration_months, 36)

    def test_service_defaults_to_service_warranty(self):
        product = self.env['product.product'].create({
            'name': 'Service Product',
            'type': 'service',
        })
        self.assertEqual(product.condition_grade_value_id.name, 'New')
        self.assertEqual(product.warranty_policy_id.duration_months, 3)

    def test_condition_grade_updates_factor_and_warranty(self):
        product = self.env['product.product'].create({
            'name': 'Gradeable Item',
            'categ_id': self.category.id,
        })
        product.condition_grade_value_id = self.env.ref(
            'resale.product_attribute_value_condition_very_good'
        )
        self.assertEqual(product.condition_id.code, 'VG')
        self.assertEqual(product.condition_factor, 0.9)
        self.assertEqual(product.warranty_policy_id.duration_months, 12)
