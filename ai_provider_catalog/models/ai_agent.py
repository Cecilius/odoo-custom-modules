from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.addons.ai.utils.llm_providers import PROVIDERS


class AIAgent(models.Model):
    _inherit = 'ai.agent'

    @api.model
    def _get_llm_model_selection(self):
        """Combine Odoo's built-ins with approved dynamic provider models."""
        selection = list(super()._get_llm_model_selection())
        original_selection = dict(selection)
        configured_models = set(
            self.env['ai.agent'].sudo().search([]).mapped('llm_model')
        )
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

        # Keep models already assigned to an agent selectable during migration
        # after an administrator disallows them or a provider deactivates them.
        selected_ids = {model_id for model_id, __ in selection}
        selection.extend(
            (model_id, original_selection[model_id])
            for model_id in configured_models
            if model_id in original_selection and model_id not in selected_ids
        )
        for model_name in ('ai.openrouter.model', 'ai.google.model'):
            if model_name not in self.env:
                continue
            catalog_records = self.env[model_name].with_context(
                active_test=False,
            ).sudo().search([
                ('model_id', 'in', list(configured_models - selected_ids)),
            ])
            selection.extend(
                (record.model_id, record.name)
                for record in catalog_records
                if record.model_id not in selected_ids
            )
            selected_ids.update(record.model_id for record in catalog_records)
        return selection

    def _get_provider(self):
        """Resolve dynamic catalog models before falling back to Odoo."""
        self.ensure_one()
        for model_name, provider_name in (
            ('ai.openrouter.model', 'openrouter'),
            ('ai.google.model', 'google'),
        ):
            if model_name not in self.env:
                continue
            record = self.env[model_name].with_context(active_test=False).sudo().search([
                ('model_id', '=', self.llm_model),
            ], limit=1)
            if record:
                if record.active:
                    return provider_name
                raise UserError(_('The selected AI model is no longer available.'))
        return super()._get_provider()

    def _generate_response(self, *args, **kwargs):
        """Pass the agent's web-search preference into the AI service context."""
        self.ensure_one()
        if self.web_search:
            self = self.with_context(
                ai_web_search=True,
                ai_web_search_max_results=self.web_search_max_results,
            )
        return super()._generate_response(*args, **kwargs)

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
