from odoo.tests.common import TransactionCase


class TestManufacturerWizard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env['resale.product'].create({
            'name': 'GPSR Test Product',
            'ean': '4006381333931',
        })

    def _wizard(self):
        return self.env['resale.ai.manufacturer.wizard'].with_context(
            default_resale_product_id=self.product.id,
        ).create({'resale_product_id': self.product.id})

    def test_context_text_lists_identifiers(self):
        wizard = self._wizard()
        self.assertIn('EAN: 4006381333931', wizard.product_display)

    def test_new_shared_company_is_created_once(self):
        wizard = self._wizard()
        company = {
            'name': 'Acme Test Electronics GmbH',
            'street': 'Hauptstrasse 1',
            'city': 'Berlin',
            'country': 'Germany',
            'website': 'https://acme-test.example',
        }
        wizard._apply_result({
            'manufacturer': company,
            'eu_responsible': company,
            'ce_compliance': ' CE marked ',
            'safety_record': 'No recalls',
        })
        self.assertEqual(wizard.m_country_id, self.env.ref('base.de'))
        self.assertEqual(wizard.manufacturer_action, 'create')
        self.assertTrue(wizard.same_company_note)

        wizard.action_apply()
        self.assertEqual(self.product.manufacturer_id.name, 'Acme Test Electronics GmbH')
        self.assertEqual(self.product.manufacturer_id, self.product.eu_responsible_person_id)
        self.assertEqual(self.product.ce_compliance, 'CE marked')
        self.assertEqual(
            self.env['res.partner'].search_count([('name', '=', 'Acme Test Electronics GmbH')]), 1,
        )

    def test_existing_contact_is_recommended(self):
        existing = self.env['res.partner'].create({
            'name': 'Known Maker SA', 'is_company': True, 'email': 'info@knownmaker.example',
        })
        wizard = self._wizard()
        wizard._apply_result({'manufacturer': {'name': 'Known Maker SA'}})
        self.assertEqual(wizard.manufacturer_action, 'use_existing')
        self.assertEqual(wizard.manufacturer_use_partner_id, existing)
        wizard.action_apply()
        self.assertEqual(self.product.manufacturer_id, existing)
