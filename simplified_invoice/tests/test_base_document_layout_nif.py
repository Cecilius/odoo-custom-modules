from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestBaseDocumentLayoutNif(TransactionCase):
    def test_company_registry_available_on_wizard(self):
        self.env.company.company_registry = 'B12345678'
        wizard = self.env['base.document.layout'].create({'company_id': self.env.company.id})
        self.assertEqual(wizard.company_registry, 'B12345678')