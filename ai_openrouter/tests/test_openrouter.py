from unittest.mock import patch

from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError

from odoo.addons.ai.utils.llm_api_service import LLMApiService
from odoo.addons.ai.utils.llm_providers import get_provider_for_embedding_model


@tagged('-at_install', 'post_install')
class TestOpenRouter(TransactionCase):

    def setUp(self):
        super().setUp()
        self.env['ir.config_parameter'].sudo().set_param('ai.openrouter_key', 'test-key')
        self.env['ir.config_parameter'].sudo().set_param('ai.google_key', 'test-google-key')

    def test_provider_registration(self):
        for model_id, name in [
            ('nvidia/nemotron-3.5-lightning:free', 'Nemotron 3.5 Lightning (free)'),
            ('liquid/lfm-2.5-2.6b:free', 'LFM2.5-2.6B (free)'),
        ]:
            model = self.env['ai.openrouter.model'].search([
                ('model_id', '=', model_id),
            ], limit=1)
            if model:
                model.write({'name': name, 'active': True, 'allowed': True})
            else:
                self.env['ai.openrouter.model'].create({
                    'model_id': model_id,
                    'name': name,
                    'allowed': True,
                })
        agent = self.env['ai.agent'].new({
            'llm_model': 'nvidia/nemotron-3.5-lightning:free',
        })
        self.assertEqual(agent._get_provider(), 'openrouter')
        agent.llm_model = 'liquid/lfm-2.5-2.6b:free'
        self.assertEqual(agent._get_provider(), 'openrouter')
        self.assertEqual(
            get_provider_for_embedding_model(self.env, 'openai/text-embedding-3-small'),
            'openrouter',
        )
        field_selection = self.env['ai.agent']._fields['llm_model'].selection(self.env['ai.agent'])
        self.assertIn(
            ('nvidia/nemotron-3.5-lightning:free', 'Nemotron 3.5 Lightning (free)'),
            field_selection,
        )

    @patch.object(LLMApiService, '_request')
    def test_chat_completion_payload(self, request):
        request.return_value = {
            'choices': [{'message': {'role': 'assistant', 'content': 'Hello'}}],
        }
        service = LLMApiService(self.env, provider='openrouter')

        result = service.request_llm(
            llm_model='liquid/lfm-2.5-2.6b:free',
            system_prompts=['You are concise.'],
            user_prompts=['Say hello.'],
        )

        self.assertEqual(result, ['Hello'])
        request.assert_called_once()
        self.assertEqual(request.call_args.kwargs['endpoint'], '/chat/completions')
        self.assertEqual(request.call_args.kwargs['body']['model'], 'liquid/lfm-2.5-2.6b:free')
        self.assertEqual(request.call_args.kwargs['headers']['Authorization'], 'Bearer test-key')

    @patch.object(LLMApiService, '_request')
    def test_tool_call_round_trip_payload(self, request):
        request.side_effect = [
            {
                'choices': [{
                    'message': {
                        'role': 'assistant',
                        'tool_calls': [{
                            'id': 'call-1',
                            'type': 'function',
                            'function': {'name': 'lookup', 'arguments': '{"value": 1}'},
                        }],
                    },
                }],
            },
            {'choices': [{'message': {'role': 'assistant', 'content': 'Finished'}}]},
        ]
        service = LLMApiService(self.env, provider='openrouter')
        tools = {
            'lookup': ('Look up a value', True, lambda arguments: ('result', None), {
                'type': 'object',
                'properties': {'value': {'type': 'integer'}},
                'required': ['value'],
            }),
        }

        self.assertEqual(
            service.request_llm(
                'nvidia/nemotron-3.5-lightning:free', [], ['Run lookup'], tools=tools,
            ),
            ['Finished'],
        )
        second_body = request.call_args_list[1].kwargs['body']
        self.assertEqual(second_body['messages'][-2]['role'], 'assistant')
        self.assertEqual(second_body['messages'][-1]['role'], 'tool')
        self.assertEqual(second_body['messages'][-1]['tool_call_id'], 'call-1')

    @patch.object(LLMApiService, '_request')
    def test_embedding_payload(self, request):
        request.return_value = {
            'data': [{'embedding': [0.1] * 1536, 'index': 0, 'object': 'embedding'}],
        }
        service = LLMApiService(self.env, provider='openrouter')

        response = service.get_embedding(
            input='A test document',
            dimensions=1536,
            model='openai/text-embedding-3-small',
        )

        self.assertEqual(len(response['data'][0]['embedding']), 1536)
        self.assertEqual(request.call_args.kwargs['endpoint'], '/embeddings')
        self.assertEqual(request.call_args.kwargs['body']['model'], 'openai/text-embedding-3-small')

    @patch.object(LLMApiService, '_request')
    def test_model_sync_applies_guardrails(self, request):
        request.return_value = {
            'data': [
                {
                    'id': 'provider/supported-model',
                    'name': 'Supported model',
                    'architecture': {
                        'input_modalities': ['text'],
                        'output_modalities': ['text'],
                    },
                    'supported_parameters': ['tools', 'temperature'],
                    'context_length': 8192,
                    'pricing': {
                        'prompt': '0.0000015',
                        'completion': '0.000004',
                        'request': '0.001',
                        'web_search': '0.002',
                    },
                },
                {
                    'id': 'provider/no-tools',
                    'name': 'No tools model',
                    'architecture': {
                        'input_modalities': ['text'],
                        'output_modalities': ['text'],
                    },
                    'supported_parameters': ['temperature'],
                },
                {
                    'id': 'provider/image-output',
                    'name': 'Image output model',
                    'architecture': {
                        'input_modalities': ['text'],
                        'output_modalities': ['text', 'image'],
                    },
                    'supported_parameters': ['tools'],
                },
            ],
            'links': {'next': None},
        }

        count = self.env['ai.openrouter.model'].action_sync_models()

        self.assertEqual(count, 1)
        model = self.env['ai.openrouter.model'].search([
            ('model_id', '=', 'provider/supported-model'),
        ])
        self.assertTrue(model.active)
        self.assertFalse(model.allowed)
        self.assertEqual(model.context_length, 8192)
        self.assertEqual(model.prompt_cost_per_million, 1.5)
        self.assertEqual(model.completion_cost_per_million, 4)
        self.assertEqual(model.request_cost, 0.001)
        self.assertEqual(model.web_search_cost, 0.002)
        self.assertNotIn(
            ('provider/supported-model', 'Supported model'),
            self.env['ai.openrouter.model'].get_selection(),
        )
        model.allowed = True
        self.assertIn(
            ('provider/supported-model', 'Supported model'),
            self.env['ai.openrouter.model'].get_selection(),
        )
        agent = self.env['ai.agent'].new({'llm_model': 'provider/supported-model'})
        self.assertEqual(agent._get_provider(), 'openrouter')

        request.assert_called_once()
        self.assertEqual(request.call_args.kwargs['endpoint'], '/models')
        self.assertEqual(request.call_args.kwargs['params']['supported_parameters'], 'tools')

    @patch.object(LLMApiService, '_request')
    def test_web_search_is_bounded(self, request):
        request.return_value = {
            'choices': [{'message': {'role': 'assistant', 'content': 'Search result'}}],
        }
        service = LLMApiService(
            self.env(context={
                'ai_web_search': True,
                'ai_web_search_max_results': 99,
            }),
            provider='openrouter',
        )

        self.assertEqual(service.request_llm('provider/model', [], ['Search']), ['Search result'])
        self.assertEqual(request.call_args.kwargs['body']['plugins'], [{
            'id': 'web',
            'max_results': 5,
        }])

    @patch.object(LLMApiService, '_request')
    def test_existing_disallowed_model_remains_selectable(self, request):
        request.return_value = {
            'data': [{
                'id': 'provider/migrating-model',
                'name': 'Migrating model',
                'architecture': {'input_modalities': ['text'], 'output_modalities': ['text']},
                'supported_parameters': ['tools'],
            }],
            'links': {'next': None},
        }
        self.env['ai.openrouter.model'].action_sync_models()
        model = self.env['ai.openrouter.model'].search([
            ('model_id', '=', 'provider/migrating-model'),
        ])
        agent = self.env['ai.agent'].create({
            'name': 'Migration test agent',
            'llm_model': model.model_id,
        })
        model.write({'active': False, 'allowed': False})

        self.assertIn(
            (model.model_id, model.name),
            self.env['ai.agent']._fields['llm_model'].selection(self.env['ai.agent']),
        )
        agent.unlink()

    @patch.object(LLMApiService, '_request')
    def test_sync_preserves_omitted_prices(self, request):
        model_payload = {
            'id': 'provider/priced-model',
            'name': 'Priced model',
            'architecture': {'input_modalities': ['text'], 'output_modalities': ['text']},
            'supported_parameters': ['tools'],
            'pricing': {'prompt': '0.000001', 'completion': '0.000002'},
        }
        request.return_value = {'data': [model_payload], 'links': {'next': None}}
        self.env['ai.openrouter.model'].action_sync_models()
        model = self.env['ai.openrouter.model'].search([
            ('model_id', '=', 'provider/priced-model'),
        ])

        model_payload.pop('pricing')
        self.env['ai.openrouter.model'].action_sync_models()

        self.assertEqual(model.prompt_cost_per_million, 1)
        self.assertEqual(model.completion_cost_per_million, 2)

    @patch.object(LLMApiService, '_request')
    def test_empty_model_sync_is_reported(self, request):
        request.return_value = {'data': [], 'links': {'next': None}}

        with self.assertRaises(UserError):
            self.env['ai.openrouter.model'].action_sync_models()

    @patch.object(LLMApiService, '_request')
    def test_invalid_chat_response_is_reported(self, request):
        request.return_value = {'choices': []}
        service = LLMApiService(self.env, provider='openrouter')

        with self.assertRaises(UserError):
            service.request_llm('provider/model', [], ['Hello'])
