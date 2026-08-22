from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.ai.utils.llm_providers import PROVIDERS


class AIAgent(models.Model):
    _inherit = 'ai.agent'

    @api.model
    def _get_llm_model_selection(self):
        selection = list(super()._get_llm_model_selection())
        if 'ai.google.model' in self.env and self.env['ai.google.model'].search_count([]):
            google_model_ids = {
                model_id
                for provider in PROVIDERS
                if provider.name == 'google'
                for model_id, __ in provider.llms
            }
            selection = [item for item in selection if item[0] not in google_model_ids]
        for model_name in ('ai.openrouter.model', 'ai.google.model'):
            if model_name not in self.env:
                continue
            existing_ids = {model_id for model_id, __ in selection}
            selection.extend(
                (model_id, label)
                for model_id, label in self.env[model_name].get_selection()
                if model_id not in existing_ids
            )
        return selection

    llm_model = fields.Selection(
        selection=_get_llm_model_selection,
        string='LLM Model',
        default='gpt-4o',
        required=True,
    )
    web_search = fields.Boolean(
        string='Enable web search',
        help='Allow the selected provider to add web search results to the initial model request. This may incur extra provider costs.',
    )
    web_search_max_results = fields.Integer(
        string='Maximum web results',
        default=3,
        required=True,
        help='Maximum number of web results for providers that support this limit. The limit is capped at 5.',
    )

    @api.onchange('llm_model')
    def _onchange_llm_model_reset_web_search(self):
        self.web_search = False

    @api.constrains('web_search_max_results')
    def _check_web_search_max_results(self):
        if any(agent.web_search_max_results < 1 or agent.web_search_max_results > 5 for agent in self):
            raise ValidationError('The maximum number of web results must be between 1 and 5.')
