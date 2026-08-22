from odoo import fields, models


class ResaleAINameLine(models.TransientModel):
    _name = 'resale.ai.name.line'
    _description = 'Resale AI Translated Product Name'

    wizard_id = fields.Many2one('resale.ai.intake.wizard', required=True, ondelete='cascade')
    lang_code = fields.Char(required=True, readonly=True)
    language_name = fields.Char(required=True, readonly=True)
    name = fields.Char(string='Product Name')
    ai_name = fields.Char(string='AI Suggestion', readonly=True)
