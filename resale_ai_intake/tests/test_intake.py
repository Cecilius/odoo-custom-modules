import json

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestResaleAIIntake(TransactionCase):

    def test_parse_json_response(self):
        wizard = self.env['resale.ai.intake.wizard']
        result = wizard._parse_response([
            '```json',
            json.dumps({'name': 'Test Product', 'confidence': 0.9}),
            '```',
        ])
        self.assertEqual(result['name'], 'Test Product')

    def test_identifier_format_validation(self):
        wizard = self.env['resale.ai.intake.wizard'].new({
            'input_search_text': 'rose pink Galaxy Watch SM-R860',
        })
        self.assertEqual(wizard._clean_identifier('ean', ' 1234567890123 '), '1234567890123')
        self.assertEqual(wizard._clean_identifier('upc', '123-456-789-012'), '123456789012')
        self.assertEqual(wizard._clean_identifier('asin', 'b000000000'), 'B000000000')
        with self.assertRaises(UserError):
            wizard._clean_identifier('upc', '1234567890123')

    def test_active_language_name_lines_are_created(self):
        partner = self.env['res.partner'].create({'name': 'AI Intake Supplier 4'})
        batch = self.env['resale.acquisition.batch'].create({'partner_id': partner.id})
        wizard = self.env['resale.ai.intake.wizard'].create({'batch_id': batch.id})
        wizard._apply_result({
            'name': 'Test Product',
            'names': {'en_US': 'Test Product', 'es_ES': 'Producto de Prueba'},
            'sources': [],
            'confidence': 0.9,
        }, self.env['ai.agent'])
        self.assertTrue(wizard.name_line_ids)
        self.assertTrue(wizard.name_line_ids.filtered(lambda line: line.lang_code == 'en_US'))

    def test_parse_invalid_response(self):
        with self.assertRaises(UserError):
            self.env['resale.ai.intake.wizard']._parse_response(['not json'])

    def test_default_configuration_exists(self):
        configuration = self.env['resale.ai.configuration'].get_default()
        self.assertEqual(configuration.name, 'Default')
        self.assertTrue(configuration.automatic_fallback)

    def test_new_brand_attribute_value_is_selectable(self):
        value = self.env['product.attribute.value'].create({
            'name': 'Test Brand',
            'attribute_id': self.env.ref('resale.product_attribute_brand').id,
        })
        self.assertTrue(value.resale_is_brand)

    def test_error_can_return_to_input(self):
        partner = self.env['res.partner'].create({'name': 'AI Intake Supplier'})
        batch = self.env['resale.acquisition.batch'].create({
            'partner_id': partner.id,
        })
        wizard = self.env['resale.ai.intake.wizard'].create({
            'batch_id': batch.id,
            'identifier': 'TEST-EAN',
            'state': 'error',
            'error_message': 'Temporary provider error',
            'raw_agent_response': 'not json',
        })

        wizard.action_reset_input()

        self.assertEqual(wizard.state, 'input')
        self.assertEqual(wizard.identifier, 'TEST-EAN')
        self.assertFalse(wizard.error_message)
        self.assertFalse(wizard.raw_agent_response)

    def test_lookup_requires_identifier(self):
        partner = self.env['res.partner'].create({'name': 'AI Intake Supplier 2'})
        batch = self.env['resale.acquisition.batch'].create({
            'partner_id': partner.id,
        })
        wizard = self.env['resale.ai.intake.wizard'].create({
            'batch_id': batch.id,
        })
        with self.assertRaises(UserError):
            wizard.action_lookup_from_identifiers(False, False)

        wizard.action_lookup_from_identifiers(False, False, False, 'rose pink Galaxy Watch SM-R860')
        self.assertEqual(wizard.input_search_text, 'rose pink Galaxy Watch SM-R860')

    def test_lookup_popup_and_parent_targets(self):
        partner = self.env['res.partner'].create({'name': 'AI Intake Supplier 3'})
        batch = self.env['resale.acquisition.batch'].create({
            'partner_id': partner.id,
        })
        wizard = self.env['resale.ai.intake.wizard'].create({
            'batch_id': batch.id,
        })

        popup_action = wizard.action_open_identifier_popup()
        parent_action = wizard._reload_action()

        self.assertEqual(popup_action['target'], 'new')
        self.assertEqual(parent_action['target'], 'current')
