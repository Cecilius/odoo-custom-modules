from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    openrouter_key_enabled = fields.Boolean(
        string='Enable custom OpenRouter API key',
        compute='_compute_openrouter_key_enabled',
        readonly=False,
        groups='base.group_system',
    )
    openrouter_key = fields.Char(
        string='OpenRouter API key',
        config_parameter='ai.openrouter_key',
        readonly=False,
        groups='base.group_system',
    )
    openrouter_http_referer = fields.Char(
        string='OpenRouter HTTP referer',
        config_parameter='ai.openrouter_http_referer',
        groups='base.group_system',
    )
    openrouter_title = fields.Char(
        string='OpenRouter application title',
        config_parameter='ai.openrouter_title',
        groups='base.group_system',
    )

    @api.depends('openrouter_key')
    def _compute_openrouter_key_enabled(self):
        for record in self:
            record.openrouter_key_enabled = bool(record.openrouter_key)

    def action_sync_openrouter_models(self):
        self.ensure_one()
        count = self.env['ai.openrouter.model'].action_sync_models()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _('%s compatible OpenRouter models synchronized. Review the allowed-model list before using them.', count),
                'sticky': False,
            },
        }

    def action_open_openrouter_models(self):
        self.ensure_one()
        return self.env['ai.openrouter.model'].action_open_model_management()
