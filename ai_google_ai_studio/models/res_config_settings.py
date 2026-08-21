from odoo import _, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    google_key_enabled = fields.Boolean(
        string='Enable custom Google API key',
        compute='_compute_google_key_enabled',
        readonly=False,
        groups='base.group_system',
    )
    google_key = fields.Char(
        string='Google AI API key',
        config_parameter='ai.google_key',
        readonly=False,
        groups='base.group_system',
    )

    def _compute_google_key_enabled(self):
        for record in self:
            record.google_key_enabled = bool(record.google_key)

    def action_sync_google_models(self):
        self.ensure_one()
        count = self.env['ai.google.model'].action_sync_models()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _('%s compatible Google Gemini models synchronized. Review the allowed-model list before using them.', count),
                'sticky': False,
            },
        }

    def action_open_google_models(self):
        self.ensure_one()
        return self.env['ai.google.model'].action_open_model_management()
