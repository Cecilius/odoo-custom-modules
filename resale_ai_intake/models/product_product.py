from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    ai_lookup_agent_id = fields.Many2one('ai.agent', string='AI Lookup Agent', copy=False)
    ai_lookup_date = fields.Datetime(string='AI Lookup Date', copy=False)
    ai_lookup_confidence = fields.Float(string='AI Lookup Confidence', copy=False)
    ai_lookup_identifier = fields.Char(string='AI Lookup Identifier', copy=False)
    ai_lookup_sources = fields.Text(string='AI Lookup Sources', copy=False)
    ai_lookup_raw = fields.Text(string='AI Lookup Raw Response', copy=False)
    ai_retail_price_current = fields.Monetary(
        string='AI Current Retail Price', currency_field='currency_id', copy=False,
    )
    ai_retail_price_low_180 = fields.Monetary(
        string='AI Lowest Retail Price (180 days)', currency_field='currency_id', copy=False,
    )
