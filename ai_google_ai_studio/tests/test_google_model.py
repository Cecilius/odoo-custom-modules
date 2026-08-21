from unittest.mock import patch

from odoo.tests import TransactionCase, tagged
from unittest.mock import patch

from odoo.addons.ai.utils.llm_api_service import LLMApiService
from odoo.addons.ai.utils.llm_providers import get_provider


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
        self.assertEqual(get_provider(self.env, 'gemini-3.0-flash'), 'google')
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
