from unittest.mock import patch

import requests
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError

from odoo.addons.ai.utils.llm_api_service import LLMApiService
from odoo.addons.ai_provider_catalog.hooks import get_llm_request_handler


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

    def _create_interactions_model(self, model_id='gemini-3.6-flash'):
        return self.env['ai.google.model'].create({
            'model_id': model_id,
            'name': 'Gemini 3.6 Flash',
            'api_mode': 'interactions',
        })

    @patch.object(LLMApiService, '_request')
    def test_interactions_single_turn(self, request):
        self._create_interactions_model()
        request.return_value = {
            'id': 'ix_1',
            'status': 'completed',
            'steps': [
                {'type': 'model_output', 'content': [{'type': 'text', 'text': 'Hello from interactions.'}]},
            ],
        }

        service = LLMApiService(self.env, provider='google')
        self.assertEqual(
            service.request_llm('gemini-3.6-flash', ['Be concise'], ['Say hi']),
            ['Hello from interactions.'],
        )
        kwargs = request.call_args.kwargs
        self.assertEqual(kwargs['base_url'], 'https://generativelanguage.googleapis.com/v1')
        self.assertEqual(kwargs['endpoint'], '/interactions')
        self.assertEqual(kwargs['headers'], {'x-goog-api-key': 'test-google-key'})
        body = kwargs['body']
        self.assertEqual(body['model'], 'gemini-3.6-flash')
        self.assertEqual(body['system_instruction'], 'Be concise')
        self.assertEqual(body['input'], 'Say hi')

    @patch.object(LLMApiService, '_request')
    def test_interactions_tool_loop(self, request):
        self._create_interactions_model()
        request.side_effect = [
            {
                'id': 'ix_1',
                'status': 'requires_action',
                'steps': [{
                    'type': 'function_call',
                    'id': 'call_1',
                    'name': 'get_weather',
                    'arguments': {'location': 'Paris'},
                }],
            },
            {
                'id': 'ix_2',
                'status': 'completed',
                'steps': [
                    {'type': 'model_output', 'content': [{'type': 'text', 'text': 'It is sunny in Paris.'}]},
                ],
            },
        ]

        service = LLMApiService(self.env, provider='google')
        tools = {
            'get_weather': (
                'Get the weather',
                False,
                lambda arguments: 'sunny',
                {'type': 'object', 'properties': {}},
            ),
        }
        self.assertEqual(
            service.request_llm('gemini-3.6-flash', [], ['What is the weather?'], tools=tools),
            ['It is sunny in Paris.'],
        )
        first_body = request.call_args_list[0].kwargs['body']
        self.assertEqual(first_body['tools'], [{
            'type': 'function',
            'name': 'get_weather',
            'description': 'Get the weather',
            'parameters': {'type': 'object', 'properties': {}},
        }])
        second_body = request.call_args_list[1].kwargs['body']
        self.assertEqual(second_body['previous_interaction_id'], 'ix_1')
        self.assertEqual(second_body['input'], [{
            'type': 'function_result',
            'call_id': 'call_1',
            'name': 'call_1',
            'result': 'sunny',
        }])

    @patch.object(LLMApiService, '_request')
    def test_interactions_web_search(self, request):
        self._create_interactions_model()
        request.return_value = {
            'id': 'ix_1',
            'status': 'completed',
            'steps': [
                {'type': 'model_output', 'content': [{'type': 'text', 'text': 'Grounded answer'}]},
            ],
        }

        service = LLMApiService(
            self.env(context={'ai_web_search': True}),
            provider='google',
        )
        self.assertEqual(
            service.request_llm('gemini-3.6-flash', [], ['Search']),
            ['Grounded answer'],
        )
        body = request.call_args.kwargs['body']
        self.assertEqual(body['tools'], [{'type': 'google_search', 'search_types': ['web_search']}])

    @patch.object(LLMApiService, '_request')
    def test_interactions_failed_status_raises(self, request):
        self._create_interactions_model()
        request.return_value = {
            'id': 'ix_1',
            'status': 'failed',
            'errors': [{'message': 'The model refused to answer.'}],
        }

        service = LLMApiService(self.env, provider='google')
        with self.assertRaises(UserError):
            service.request_llm('gemini-3.6-flash', [], ['Do it'])

    @patch.object(LLMApiService, '_request')
    def test_generate_content_mode_falls_back_to_legacy(self, request):
        self.env['ai.google.model'].create({
            'model_id': 'gemini-3.6-flash',
            'name': 'Gemini 3.6 Flash',
            'api_mode': 'generate_content',
        })
        request.return_value = {
            'candidates': [{'content': {'parts': [{'text': 'Legacy answer'}]}}],
        }

        service = LLMApiService(self.env, provider='google')
        self.assertEqual(
            service.request_llm('gemini-3.6-flash', [], ['Hi']),
            ['Legacy answer'],
        )
        kwargs = request.call_args.kwargs
        self.assertEqual(kwargs['endpoint'], '/models/gemini-3.6-flash:generateContent')
        self.assertIn('generationConfig', kwargs['body'])
        self.assertNotIn('generation_config', kwargs['body'])

    def test_google_handler_registered(self):
        self.assertIsNotNone(get_llm_request_handler('google'))

    def test_sync_sets_api_mode_from_methods(self):
        with patch('odoo.addons.ai_google_ai_studio.models.google_model.requests.get') as get:
            get.return_value.raise_for_status.return_value = None
            get.return_value.json.return_value = {
                'models': [
                    {
                        'name': 'models/gemini-3.6-flash',
                        'displayName': 'Gemini 3.6 Flash',
                        'supportedGenerationMethods': ['interactions', 'generateContent'],
                    },
                    {
                        'name': 'models/gemini-2.5-flash',
                        'displayName': 'Gemini 2.5 Flash',
                        'supportedGenerationMethods': ['generateContent'],
                    },
                ]
            }
            self.env['ai.google.model'].action_sync_models()

        self.assertEqual(
            self.env['ai.google.model'].search([('model_id', '=', 'gemini-3.6-flash')]).api_mode,
            'interactions',
        )
        self.assertEqual(
            self.env['ai.google.model'].search([('model_id', '=', 'gemini-2.5-flash')]).api_mode,
            'generate_content',
        )
