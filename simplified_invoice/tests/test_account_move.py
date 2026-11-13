from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestSimplifiedInvoiceWorkflow(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('es')
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data['company']
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
        cls.company.l10n_es_simplified_invoice_limit = 50.0

    def _make_invoice(self, journal, vat=False, price_unit=10.0, simplified=False):
        partner = self.partner.copy({"vat": "ES12345678Z" if vat else False})
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "currency_id": self.company.currency_id.id,
            "journal_id": journal.id,
            "invoice_line_ids": [(0, 0, {
                "name": "Line",
                "quantity": 1.0,
                "price_unit": price_unit,
                "product_id": self.product.id,
            })],
        })
        move.l10n_es_is_simplified = simplified
        return move

    def test_over_limit_non_spanish_without_vat_not_blocked_by_spanish_rule(self):
        non_spanish_partner = self.env["res.partner"].create({
            "name": "Non ES Customer",
            "country_id": self.env.ref("base.fr").id,
            "vat": False,
        })
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": non_spanish_partner.id,
            "currency_id": self.company.currency_id.id,
            "journal_id": self.journal_full.id,
            "invoice_line_ids": [(0, 0, {
                "name": "Line",
                "quantity": 1.0,
                "price_unit": 100.0,
                "product_id": self.product.id,
            })],
        })
        # This should not be blocked by the Spanish VAT rule.
        move.action_post()

    def test_empty_move_set_can_be_posted(self):
        self.env["account.move"].browse([]).action_post()

    def test_simplified_invoice_cannot_be_rendered_as_proforma(self):
        move = self._make_invoice(
            self.journal_simplified,
            vat=False,
            price_unit=10.0,
            simplified=True,
        )

        with self.assertRaises(UserError):
            self.env["ir.actions.report"]._pre_render_qweb_pdf(
                "account.account_invoices",
                move.ids,
                data={"proforma": True},
            )

    def test_under_limit_non_spanish_eu_customer_is_not_simplified(self):
        non_spanish_partner = self.env["res.partner"].create({
            "name": "French Customer",
            "country_id": self.env.ref("base.fr").id,
            "vat": False,
        })
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": non_spanish_partner.id,
            "currency_id": self.company.currency_id.id,
            "journal_id": self.journal_full.id,
            "invoice_line_ids": [(0, 0, {
                "name": "Line",
                "quantity": 1.0,
                "price_unit": 10.0,
                "product_id": self.product.id,
            })],
        })

        self.assertFalse(move.l10n_es_is_simplified)

    def test_simplified_invoice_for_non_spanish_customer_raises_usererror(self):
        non_spanish_partner = self.env["res.partner"].create({
            "name": "Non ES Customer",
            "country_id": self.env.ref("base.fr").id,
            "vat": False,
        })
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": non_spanish_partner.id,
            "currency_id": self.company.currency_id.id,
            "journal_id": self.journal_simplified.id,
            "invoice_line_ids": [(0, 0, {
                "name": "Line",
                "quantity": 1.0,
                "price_unit": 10.0,
                "product_id": self.product.id,
            })],
        })
        move.l10n_es_is_simplified = True
        with self.assertRaises(UserError):
            move.action_post()

    def test_simplified_invoice_for_company_customer_raises_usererror(self):
        company_partner = self.env["res.partner"].create({
            "name": "Spanish Company Customer",
            "country_id": self.env.ref("base.es").id,
            "company_type": "company",
            "vat": "ESB12345674",
        })
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": company_partner.id,
            "currency_id": self.company.currency_id.id,
            "journal_id": self.journal_simplified.id,
            "invoice_line_ids": [(0, 0, {
                "name": "Line",
                "quantity": 1.0,
                "price_unit": 10.0,
                "product_id": self.product.id,
            })],
        })
        move.l10n_es_is_simplified = True
        with self.assertRaises(UserError):
            move.action_post()

    def test_over_limit_simplified_invoice_raises_usererror(self):
        move = self._make_invoice(
            self.journal_simplified,
            vat=True,
            price_unit=100.0,
            simplified=True,
        )
        with self.assertRaises(UserError):
            move.action_post()

    def test_full_invoice_for_spanish_customer_without_vat_raises_usererror(self):
        move = self._make_invoice(
            self.journal_full,
            vat=False,
            price_unit=10.0,
            simplified=False,
        )
        # Partner is Spanish by default (base.es), and company is also Spanish.
        with self.assertRaises(UserError):
            move.action_post()

    def test_over_limit_invoice_without_vat_raises_usererror(self):
        move = self._make_invoice(
            self.journal_full,
            vat=False,
            price_unit=100.0,
            simplified=False,
        )
        with self.assertRaises(UserError):
            move.action_post()

    def test_journal_mismatch_opens_wizard(self):
        move = self._make_invoice(
            self.journal_full,
            vat=True,
            price_unit=10.0,
            simplified=True,
        )
        action = move.action_post()
        self.assertEqual(action["res_model"], "simplified.invoice.post.wizard")
        self.assertEqual(action["target"], "new")
        self.assertEqual(action["context"]["default_move_id"], move.id)

    def test_batch_action_post_posts_every_valid_invoice(self):
        moves = (
            self._make_invoice(self.journal_full, vat=True, price_unit=10.0)
            | self._make_invoice(self.journal_full, vat=True, price_unit=20.0)
        )
        moves.action_post()
        self.assertEqual(set(moves.mapped("state")), {"posted"})

    def test_list_view_batch_posting_enforces_rules(self):
        """The 'Post entries' wizard calls _post() directly and must not skip the rules."""
        valid = self._make_invoice(self.journal_full, vat=True, price_unit=10.0)
        invalid = self._make_invoice(self.journal_full, vat=False, price_unit=10.0, simplified=False)
        wizard = self.env["validate.account.move"].with_context(
            active_model="account.move",
            active_ids=(valid | invalid).ids,
        ).create({})
        with self.assertRaises(UserError):
            wizard.validate_move()

    def test_amount_equal_to_limit_may_stay_simplified(self):
        untaxed_product = self.env["product.product"].create({
            "name": "Untaxed Product",
            "type": "service",
            "taxes_id": [(5, 0, 0)],
        })
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner.id,
            "journal_id": self.journal_simplified.id,
            "invoice_line_ids": [(0, 0, {
                "name": "Line",
                "quantity": 1.0,
                "price_unit": 50.0,
                "product_id": untaxed_product.id,
                "tax_ids": [(5, 0, 0)],
            })],
        })
        move.l10n_es_is_simplified = True
        self.assertFalse(move._is_over_simplified_limit())
        move.action_post()
        self.assertEqual(move.state, "posted")
