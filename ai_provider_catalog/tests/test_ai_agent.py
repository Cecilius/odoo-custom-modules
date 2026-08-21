from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged('-at_install', 'post_install')
class TestAIAgentCatalog(TransactionCase):

    def test_changing_model_resets_web_search(self):
        agent = self.env['ai.agent'].new({
            'llm_model': 'gpt-4o',
            'web_search': True,
        })
        agent.llm_model = 'gpt-4o'
        agent._onchange_llm_model_reset_web_search()
        self.assertFalse(agent.web_search)

    def test_web_search_result_limit(self):
        agent = self.env['ai.agent'].new({'web_search_max_results': 6})
        with self.assertRaises(ValidationError):
            agent._check_web_search_max_results()
