# Part of Odoo. See LICENSE file for full copyright and licensing details.
import psycopg2

from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestResaleItem(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.category = cls.env['resale.category'].create({
            'name': 'Test Category',
            'code': 'TC',
        })
        cls.brand = cls.env['resale.brand'].create({'name': 'TestBrand'})
        cls.partner = cls.env['res.partner'].create({'name': 'Supplier'})
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'type': 'consu',
            'is_storable': True,
            'default_code': 'RFB-TC-000001',
        })
        cls.manager = cls.env['res.users'].create({
            'name': 'Resale Manager',
            'login': 'resale_manager',
            'group_ids': [(6, 0, [cls.env.ref('resale_core.group_resale_manager').id])],
        })
        cls.user = cls.env['res.users'].create({
            'name': 'Resale User',
            'login': 'resale_user',
            'group_ids': [(6, 0, [cls.env.ref('resale_core.group_resale_user').id])],
        })

    def test_create_resale_item(self):
        item = self.env['resale.item'].create({
            'rfb': 'RFB-TC-000002',
            'category_id': self.category.id,
            'brand_id': self.brand.id,
            'model_es': 'Model ES',
            'product_id': self.product.id,
            'initial_value': 100.0,
        })
        self.assertEqual(item.name, 'RFB-TC-000002 - TestBrand - Model ES')
        self.assertEqual(item.adjusted_value, 100.0)
        self.assertEqual(item.cost_status, 'pending')

    def test_rfb_unique(self):
        self.env['resale.item'].create({
            'rfb': 'RFB-TC-000003',
            'category_id': self.category.id,
        })
        with self.assertRaises(psycopg2.errors.UniqueViolation):
            self.env['resale.item'].create({
                'rfb': 'RFB-TC-000003',
                'category_id': self.category.id,
            })

    def test_product_unique(self):
        self.env['resale.item'].create({
            'rfb': 'RFB-TC-000004',
            'category_id': self.category.id,
            'product_id': self.product.id,
        })
        with self.assertRaises(psycopg2.errors.UniqueViolation):
            self.env['resale.item'].create({
                'rfb': 'RFB-TC-000005',
                'category_id': self.category.id,
                'product_id': self.product.id,
            })

    def test_locked_cost_cannot_be_edited_by_user(self):
        item = self.env['resale.item'].create({
            'rfb': 'RFB-TC-000006',
            'category_id': self.category.id,
            'acquisition_cost': 50.0,
        })
        item.with_user(self.manager)._lock_cost()
        self.assertEqual(item.cost_status, 'locked')
        with self.assertRaises(AccessError):
            item.with_user(self.user).write({'acquisition_cost': 60.0})

    def test_user_cannot_lock_costs(self):
        item = self.env['resale.item'].create({
            'rfb': 'RFB-TC-000007',
            'category_id': self.category.id,
        })
        with self.assertRaises(AccessError):
            item.with_user(self.user)._lock_cost()
