from odoo import api, fields, models


class ResaleAIConfiguration(models.Model):
    _name = 'resale.ai.configuration'
    _description = 'Resale AI Configuration'

    name = fields.Char(required=True, default='Default')
    primary_agent_id = fields.Many2one(
        'ai.agent',
        string='Primary Lookup Agent',
        help='First agent used for EAN/ASIN product lookup.',
    )
    fallback_agent_id = fields.Many2one(
        'ai.agent',
        string='Deep Research Agent',
        help='Agent used when the primary answer is below the confidence threshold.',
    )
    secondary_agent_id = fields.Many2one(
        'ai.agent',
        string='Secondary Task Agent',
        help='Agent used for local brand/category matching and normalization.',
    )
    fallback_brand_value_id = fields.Many2one(
        'product.attribute.value',
        string='Fallback Brand Value',
        domain="[('resale_is_brand', '=', True)]",
        help='Brand value used when the AI cannot confidently identify a brand.',
    )
    confidence_threshold = fields.Float(default=0.75, required=True)
    automatic_fallback = fields.Boolean(
        default=True,
        help='Automatically call the deep research agent when confidence is low.',
    )

    @api.constrains('confidence_threshold')
    def _check_confidence_threshold(self):
        for record in self:
            if not 0.0 <= record.confidence_threshold <= 1.0:
                raise ValueError('Confidence threshold must be between 0 and 1.')

    @api.model
    def get_default(self):
        return self.search([], limit=1) or self.create({'name': 'Default'})
