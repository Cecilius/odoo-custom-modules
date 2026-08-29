from unittest.mock import patch

import requests
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError

from odoo.addons.ai.utils.llm_api_service import LLMApiService


@tagged('-at_install', 'post_install')
class TestGoogleModel(TransactionCase):

    def setUp(self):
        super().setUp()
        self.env['ir.config_parameter'].sudo().set_param('ai.google_key', 'test-google-key')

    @patch('odoo.addons.ai_google_ai_studio.models.google_model.requests.get')
    def test_model_sync(self, get):
        get.return_value.raise_for_status.return_value = None
        get.return_value.json.return_value = {
            'models': [
                {
                    'name': 'models/gemini-3.0-flash',
                    'displayName': 'Gemini 3.0 Flash',
                    'description': 'Test Gemini model',
                    'inputTokenLimit': 100000,
                    'outputTokenLimit': 8192,
                    'supportedGenerationMethods': ['generateContent'],
                },
                {
                    'name': 'models/text-embedding-005',
                    'displayName': 'Embedding model',
                    'supportedGenerationMethods': ['embedContent'],
                },
            ]
        }

        count = self.env['ai.google.model'].action_sync_models()

        self.assertEqual(count, 1)
        model = self.env['ai.google.model'].search([
            ('model_id', '=', 'gemini-3.0-flash'),
        ])
        self.assertEqual(model.input_token_limit, 100000)
        self.assertFalse(model.allowed)
        agent = self.env['ai.agent'].new({'llm_model': 'gemini-3.0-flash'})
        self.assertEqual(agent._get_provider(), 'google')
        model.allowed = True
        self.assertIn(
            ('gemini-3.0-flash', 'Gemini 3.0 Flash'),
            self.env['ai.agent']._fields['llm_model'].selection(self.env['ai.agent']),
        )

    @patch.object(LLMApiService, '_request')
    def test_google_web_search(self, request):
        request.return_value = {
            'candidates': [{
                'content': {'parts': [{'text': 'Grounded answer'}]},
            }],
        }
        service = LLMApiService(
            self.env(context={'ai_web_search': True}),
            provider='google',
        )

        self.assertEqual(
            service.request_llm('gemini-3.0-flash', [], ['Search']),
            ['Grounded answer'],
        )
        body = request.call_args.kwargs['body']
        self.assertEqual(body['tools'], {'google_search': {}})

    @patch('odoo.addons.ai_google_ai_studio.models.google_model.requests.get')
    def test_sync_deactivates_models_missing_upstream(self, get):
        get.return_value.raise_for_status.return_value = None
        get.return_value.json.return_value = {
            'models': [{
                'name': 'models/gemini-current',
                'displayName': 'Current Gemini',
                'supportedGenerationMethods': ['generateContent'],
            }],
        }
        self.env['ai.google.model'].action_sync_models()
        old_model = self.env['ai.google.model'].create({
            'model_id': 'gemini-retired',
            'name': 'Retired Gemini',
            'active': True,
        })

        self.env['ai.google.model'].action_sync_models()

        self.assertFalse(old_model.active)
        self.assertTrue(self.env['ai.google.model'].search([
            ('model_id', '=', 'gemini-current'),
        ]).active)

    @patch('odoo.addons.ai_google_ai_studio.models.google_model.requests.get')
    def test_empty_compatible_sync_does_not_change_catalog(self, get):
        existing = self.env['ai.google.model'].create({
            'model_id': 'gemini-existing',
            'name': 'Existing Gemini',
            'active': True,
        })
        get.return_value.raise_for_status.return_value = None
        get.return_value.json.return_value = {
            'models': [{
                'name': 'models/text-embedding',
                'supportedGenerationMethods': ['embedContent'],
            }],
        }

        with self.assertRaises(UserError):
            self.env['ai.google.model'].action_sync_models()

        self.assertTrue(existing.active)

    @patch('odoo.addons.ai_google_ai_studio.models.google_model.requests.get')
    def test_google_catalog_api_errors_are_user_errors(self, get):
        get.side_effect = requests.exceptions.Timeout('upstream timeout')

        with self.assertRaises(UserError):
            self.env['ai.google.model'].action_sync_models()
