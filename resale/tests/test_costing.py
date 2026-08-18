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
        cls.partner = cls.env['res.partner'].create({'name': 'Supplier'})
        cls.category = cls.env['resale.category'].create({
            'name': 'Test Category',
            'code': 'TC',
        })
        cls.user = cls.env['res.users'].create({
            'name': 'Resale User',
            'login': 'resale_user',
            'group_ids': [(6, 0, [cls.env.ref('resale.group_resale_user').id])],
        })
        cls.manager = cls.env['res.users'].create({
            'name': 'Resale Manager',
            'login': 'resale_manager',
            'group_ids': [(6, 0, [cls.env.ref('resale.group_resale_manager').id])],
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Billable Product',
            'type': 'consu',
            'is_storable': True,
        })
        cls.expense_account = cls.env['account.account'].create({
            'name': 'Test Expense',
            'code': '600001',
            'account_type': 'expense',
        })
        cls.payable_account = cls.env['account.account'].create({
            'name': 'Test Payable',
            'code': '400001',
            'account_type': 'liability_payable',
        })
        cls.product.product_tmpl_id.property_account_expense_id = cls.expense_account
        cls.partner.property_account_payable_id = cls.payable_account
        cls.purchase_journal = cls.env['account.journal'].create({
            'name': 'Purchase Journal',
            'type': 'purchase',
            'code': 'PURJ',
        })

    def _create_bill(self, amount, move_type='in_invoice'):
        return self.env['account.move'].with_context(default_move_type=move_type).create({
            'move_type': move_type,
            'journal_id': self.purchase_journal.id,
            'partner_id': self.partner.id,
            'invoice_date': '2026-08-18',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'name': self.product.name,
                'quantity': 1.0,
                'price_unit': amount,
                'tax_ids': [],
            })],
        })

    def test_bill_sync_creates_components(self):
        batch = self.env['resale.acquisition.batch'].create({
            'partner_id': self.partner.id,
        })
        bill = self._create_bill(1000.0)
        bill.action_post()
        batch.write({'bill_ids': [(4, bill.id)]})
        batch.action_sync_bills()
        self.assertEqual(len(batch.component_ids), 1)
        self.assertEqual(batch.component_ids.amount_net, 1000.0)
        self.assertEqual(batch.allocable_cost, 1000.0)

    def test_credit_note_negative_amount(self):
        batch = self.env['resale.acquisition.batch'].create({
            'partner_id': self.partner.id,
        })
        bill = self._create_bill(200.0, move_type='in_refund')
        bill.action_post()
        batch.write({'bill_ids': [(4, bill.id)]})
        batch.action_sync_bills()
        self.assertEqual(batch.component_ids.amount_net, -200.0)

    def test_locked_component_cannot_be_edited(self):
        batch = self.env['resale.acquisition.batch'].create({
            'partner_id': self.partner.id,
        })
        component = self.env['resale.cost.component'].create({
            'batch_id': batch.id,
            'name': 'Purchase',
            'component_type': 'purchase',
            'amount_net': 100.0,
            'include_in_allocable': True,
        })
        batch.state = 'locked'
        with self.assertRaises(AccessError):
            component.with_user(self.user).write({'amount_net': 200.0})
