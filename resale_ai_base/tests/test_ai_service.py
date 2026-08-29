from unittest.mock import MagicMock, patch

from odoo.addons.ai.utils.llm_api_service import LLMApiService
from odoo.addons.resale_ai_base.models.ai_service import ResaleAIRequestError
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestResaleAIService(TransactionCase):

    def test_parse_json_response_supports_fenced_json(self):
        result = self.env['resale.ai.service'].parse_json_response([
            '```json\n{"value": "ok"}\n```',
        ])
        self.assertEqual(result, {'value': 'ok'})

    def test_parse_json_response_supports_top_level_array(self):
        result = self.env['resale.ai.service'].parse_json_response(['["one", "two"]'])
        self.assertEqual(result, ['one', 'two'])

    def test_provider_user_error_becomes_retryable_request_error(self):
        agent = MagicMock()
        agent._get_provider.return_value = 'openai'
        agent.llm_model = 'gpt-4o'
        agent.web_search = False
        service = self.env['resale.ai.service']
        with patch.object(LLMApiService, 'request_llm', side_effect=UserError('provider failed')):
            with self.assertRaises(ResaleAIRequestError):
                service.request_llm(agent, [], ['prompt'])
