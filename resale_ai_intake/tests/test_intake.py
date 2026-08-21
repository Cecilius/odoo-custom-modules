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

    def test_parse_invalid_response(self):
        with self.assertRaises(UserError):
            self.env['resale.ai.intake.wizard']._parse_response(['not json'])

    def test_default_configuration_exists(self):
        configuration = self.env['resale.ai.configuration'].get_default()
        self.assertEqual(configuration.name, 'Default')
        self.assertTrue(configuration.automatic_fallback)
