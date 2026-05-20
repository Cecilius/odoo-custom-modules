from odoo.tests.common import TransactionCase


class TestSimplifiedInvoiceWorkflow(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env["res.partner"].create({"name": "Test Customer", "country_id": cls.env.ref("base.es").id})
        cls.journal_simplified = cls.env["account.journal"].create({"name": "Simplified Sales", "code": "SIMP", "type": "sale"})
        cls.journal_full = cls.env["account.journal"].create({"name": "Full Sales", "code": "FULL", "type": "sale"})
        cls.company.write({"simplified_sales_journal_id": cls.journal_simplified.id, "full_sales_journal_id": cls.journal_full.id})
        cls.product = cls.env["product.product"].create({"name": "Test Product", "type": "service", "list_price": 0.0})

    def _make_invoice(self, journal, vat=False, price_unit=1.0, simplified=False):
        partner = self.partner.copy({"vat": "ES12345678Z" if vat else False})
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "currency_id": self.company.currency_id.id,
            "journal_id": journal.id,
            "invoice_line_ids": [(0, 0, {"name": "Line", "quantity": 1.0, "price_unit": price_unit, "product_id": self.product.id})],
        })
        move.l10n_es_is_simplified = simplified
        return move

    def test_over_limit_invoice_opens_wizard(self):
        move = self._make_invoice(self.journal_full, vat=False, price_unit=100.0)
        self.company.l10n_es_simplified_invoice_limit = 0.0
        action = move.action_post()
        self.assertEqual(action["res_model"], "simplified.invoice.post.wizard")
        self.assertEqual(action["target"], "new")
        self.assertEqual(action["context"]["default_move_id"], move.id)

    def test_journal_mismatch_opens_wizard(self):
        move = self._make_invoice(self.journal_full, vat=True, price_unit=10.0, simplified=True)
        action = move.action_post()
        self.assertEqual(action["res_model"], "simplified.invoice.post.wizard")
        self.assertEqual(action["target"], "new")
        self.assertIn("default_message", action["context"])
