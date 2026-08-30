"""Configuration fields for GPSR research agents."""

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Store the primary and backup manufacturer research agents."""
    _inherit = 'res.config.settings'

    resale_ai_manufacturer_research_agent_id = fields.Many2one(
        'ai.agent', string='GPSR research agent',
        config_parameter='resale_ai_manufacturer.research_agent_id',
        help='Primary AI agent used to research manufacturer and GPSR compliance information.',
    )
    resale_ai_manufacturer_backup_agent_id = fields.Many2one(
        'ai.agent', string='Backup GPSR research agent',
        config_parameter='resale_ai_manufacturer.backup_agent_id',
        help='Secondary AI agent used when the primary agent is unavailable.',
    )
    resale_ai_manufacturer_request_timeout = fields.Integer(
        string='AI request timeout (seconds)',
        config_parameter='resale_ai_manufacturer.request_timeout',
        default=90,
        help='Minimum timeout used for each GPSR research request. The minimum allowed value is 30 seconds.',
    )
