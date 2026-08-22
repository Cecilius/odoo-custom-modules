# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestAcquisitionBatch(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True, resale_item=True))
        cls.partner = cls.env['res.partner'].create({'name': 'Supplier'})
        cls.category = cls.env['product.category'].create({
            'name': 'Test Category',
            'rfb_prefix': 'TC',
        })
        cls.manager = cls.env['res.users'].create({
            'name': 'Resale Manager',
            'login': 'resale_manager',
            'group_ids': [(6, 0, [cls.env.ref('resale.group_resale_manager').id])],
        })

    def _create_item(self, name, initial_value):
        return self.env['product.product'].create({
            'name': name,
            'categ_id': self.category.id,
            'initial_value': initial_value,
            'eval_basic_result': 'pass',
            'eval_disposition': 'sale',
        })

    def test_batch_state_transitions(self):
        batch = self.env['resale.acquisition.batch'].create({
            'partner_id': self.partner.id,
            'expected_items': 2,
        })
        self.assertTrue(batch.name.startswith('BATCH-'))
        batch.action_receive()
        self.assertEqual(batch.state, 'received')

        item_a = self._create_item('Item A', 100.0)
        item_b = self._create_item('Item B', 100.0)
        item_a.batch_id = batch.id
        item_b.batch_id = batch.id
        self.assertEqual(batch.received_items, 2)

        self.env['resale.cost.component'].create({
            'batch_id': batch.id,
            'name': 'Purchase',
            'component_type': 'purchase',
            'amount_net': 100.0,
            'include_in_allocable': True,
        })

        item_a.action_complete_evaluation()
        item_b.action_complete_evaluation()

        batch.action_calculate_allocation()
        self.assertEqual(batch.state, 'allocating')
        self.assertEqual(item_a.acquisition_cost, 50.0)
        self.assertEqual(item_b.acquisition_cost, 50.0)

        batch.with_user(self.manager).action_lock_costs()
        self.assertEqual(batch.state, 'locked')
        self.assertEqual(item_a.cost_status, 'locked')

        batch.action_done()
        self.assertEqual(batch.state, 'done')

    def test_receive_creates_native_stock_receipt(self):
        batch = self.env['resale.acquisition.batch'].create({
            'partner_id': self.partner.id,
            'expected_items': 1,
        })
        item = self._create_item('Stock Item', 100.0)
        item.batch_id = batch.id

        batch.action_receive()

        self.assertEqual(len(batch.receipt_picking_ids), 1)
        self.assertEqual(batch.receipt_picking_ids.state, 'done')
        self.assertEqual(item.qty_available, 1.0)

    def test_cannot_lock_without_evaluation(self):
        batch = self.env['resale.acquisition.batch'].create({
            'partner_id': self.partner.id,
        })
        batch.action_receive()
        item = self._create_item('Item Unevaluated', 50.0)
        item.batch_id = batch.id
        self.env['resale.cost.component'].create({
            'batch_id': batch.id,
            'name': 'Purchase',
            'component_type': 'purchase',
            'amount_net': 50.0,
            'include_in_allocable': True,
        })
        item.write({'eval_basic_result': 'pass', 'eval_disposition': 'sale'})
        item.action_complete_evaluation()
        batch.action_calculate_allocation()
        # Artificially reset eval_done to test lock gate
        item.eval_done = False
        with self.assertRaises(UserError):
            batch.with_user(self.manager).action_lock_costs()
