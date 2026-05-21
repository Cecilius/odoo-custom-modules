from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestSimplifiedInvoiceWorkflow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env["res.partner"].create({
            "name": "Test Customer",
            "country_id": cls.env.ref("base.es").id,
        })
        cls.journal_simplified = cls.env["account.journal"].create({
            "name": "Simplified Sales",
            "code": "SIMP",
            "type": "sale",
        })
        cls.journal_full = cls.env["account.journal"].create({
            "name": "Full Sales",
            "code": "FULL",
            "type": "sale",
        })
        cls.company.write({
            "simplified_sales_journal_id": cls.journal_simplified.id,
            "full_sales_journal_id": cls.journal_full.id,
        })
        cls.product = cls.env["product.product"].create({
            "name": "Test Product",
            "type": "service",
            "list_price": 0.0,
        })

    def _make_invoice(self, journal, simplified=False):
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner.id,
            "currency_id": self.company.currency_id.id,
            "journal_id": journal.id,
            "invoice_line_ids": [(0, 0, {
                "name": "Line",
                "quantity": 1.0,
                "price_unit": 10.0,
                "product_id": self.product.id,
            })],
        })
        move.l10n_es_is_simplified = simplified
        return move

    def test_journal_mismatch_opens_wizard(self):
        move = self._make_invoice(self.journal_full, simplified=True)
        action = move.action_post()
        self.assertEqual(action["res_model"], "simplified.invoice.post.wizard")

    def test_wizard_sets_simplified(self):
        move = self._make_invoice(self.journal_full, simplified=False)
        wizard = self.env["simplified.invoice.post.wizard"].create({
            "move_id": move.id,
            "message": "test",
        })
        wizard.action_set_simplified()
        self.assertEqual(move.journal_id, self.journal_simplified)
        self.assertTrue(move.l10n_es_is_simplified)

    def test_wizard_sets_full(self):
        move = self._make_invoice(self.journal_simplified, simplified=True)
        wizard = self.env["simplified.invoice.post.wizard"].create({
            "move_id": move.id,
            "message": "test",
        })
        wizard.action_set_full()
        self.assertEqual(move.journal_id, self.journal_full)
        self.assertFalse(move.l10n_es_is_simplified)

    def test_wizard_refuses_posted_move(self):
        move = self._make_invoice(self.journal_full, simplified=True)
        move.state = "posted"
        wizard = self.env["simplified.invoice.post.wizard"].create({
            "move_id": move.id,
            "message": "test",
        })
        with self.assertRaises(UserError):
            wizard.action_set_simplified()