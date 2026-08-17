# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestResaleCosting(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.category = cls.env['resale.category'].create({
            'name': 'Test Category',
            'code': 'TC',
        })
        cls.partner = cls.env['res.partner'].create({'name': 'Supplier'})
        cls.batch = cls.env['resale.acquisition.batch'].create({
            'name': 'BATCH-COST-001',
            'partner_id': cls.partner.id,
            'expected_items': 2,
            'state': 'received',
        })
        cls.item_a = cls.env['resale.item'].create({
            'rfb': 'RFB-TC-000201',
            'category_id': cls.category.id,
            'batch_id': cls.batch.id,
            'initial_value': 100.0,
        })
        cls.item_b = cls.env['resale.item'].create({
            'rfb': 'RFB-TC-000202',
            'category_id': cls.category.id,
            'batch_id': cls.batch.id,
            'initial_value': 100.0,
        })
        cls.manager = cls.env['res.users'].create({
            'name': 'Resale Manager',
            'login': 'resale_manager_cost',
            'group_ids': [(6, 0, [cls.env.ref('resale_core.group_resale_manager').id])],
        })
        cls.user = cls.env['res.users'].create({
            'name': 'Resale User',
            'login': 'resale_user_cost',
            'group_ids': [(6, 0, [cls.env.ref('resale_core.group_resale_user').id])],
        })

    def test_allocable_cost_total(self):
        self.env['resale.cost.component'].create({
            'batch_id': self.batch.id,
            'name': 'Purchase',
            'component_type': 'purchase',
            'amount_net': 100.0,
            'vat_amount': 21.0,
            'include_in_allocable': True,
        })
        self.env['resale.cost.component'].create({
            'batch_id': self.batch.id,
            'name': 'US Service Fee',
            'component_type': 'service',
            'amount_net': 30.0,
            'vat_amount': 0.0,
            'tax_treatment': 'reverse_charge',
            'include_in_allocable': True,
        })
        self.assertEqual(self.batch.allocable_cost, 130.0)
        self.assertEqual(self.batch.total_cash, 151.0)

    def test_cost_allocation(self):
        self.env['resale.cost.component'].create({
            'batch_id': self.batch.id,
            'name': 'Purchase',
            'component_type': 'purchase',
            'amount_net': 100.0,
            'include_in_allocable': True,
        })
        self.batch.action_calculate_allocation()
        self.assertEqual(self.item_a.acquisition_cost, 50.0)
        self.assertEqual(self.item_a.cost_status, 'provisional')
        self.assertEqual(self.item_b.acquisition_cost, 50.0)

    def test_cost_locking_requires_manager(self):
        self.env['resale.cost.component'].create({
            'batch_id': self.batch.id,
            'name': 'Purchase',
            'component_type': 'purchase',
            'amount_net': 100.0,
            'include_in_allocable': True,
        })
        self.batch.action_calculate_allocation()
        with self.assertRaises(AccessError):
            self.batch.with_user(self.user).action_lock_costs()
        self.batch.with_user(self.manager).action_lock_costs()
        self.assertEqual(self.batch.state, 'locked')
        self.assertEqual(self.item_a.cost_status, 'locked')

    def test_locked_component_cannot_be_edited(self):
        component = self.env['resale.cost.component'].create({
            'batch_id': self.batch.id,
            'name': 'Purchase',
            'component_type': 'purchase',
            'amount_net': 100.0,
            'include_in_allocable': True,
        })
        self.batch.action_calculate_allocation()
        self.batch.with_user(self.manager).action_lock_costs()
        with self.assertRaises(AccessError):
            component.write({'amount_net': 120.0})
