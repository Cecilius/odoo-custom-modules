from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    resale_advertisement_max_characters = fields.Integer(
        string='Long listing max characters',
        config_parameter='resale_advertisement.max_characters',
        default=2000,
        help='Maximum number of characters for an AI generated long listing proposal.',
    )
    resale_advertisement_research_agent_id = fields.Many2one(
        'ai.agent',
        string='Listing research agent',
        config_parameter='resale_advertisement.research_agent_id',
        help='Primary AI agent used to research and write listing proposals.',
    )
    resale_advertisement_backup_agent_id = fields.Many2one(
        'ai.agent',
        string='Backup listing research agent',
        config_parameter='resale_advertisement.backup_agent_id',
        help='Secondary AI agent used when the primary agent is unavailable.',
    )
    resale_advertisement_short_max_characters = fields.Integer(
        string='Short listing max characters',
        config_parameter='resale_advertisement.short_max_characters',
        default=300,
        help='Maximum number of characters for an AI generated short listing proposal.',
    )
    resale_advertisement_short_agent_id = fields.Many2one(
        'ai.agent',
        string='Short listing agent',
        config_parameter='resale_advertisement.short_agent_id',
        help='Primary AI agent used to shorten the long listing into a short listing.',
    )
    resale_advertisement_short_backup_agent_id = fields.Many2one(
        'ai.agent',
        string='Backup short listing agent',
        config_parameter='resale_advertisement.short_backup_agent_id',
        help='Secondary AI agent used when the primary short listing agent is unavailable.',
    )
