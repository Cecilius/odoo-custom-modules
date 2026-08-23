from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    resale_ai_research_agent_id = fields.Many2one('ai.agent', string='Product research agent', config_parameter='resale_ai_product.research_agent_id')
    resale_ai_backup_agent_id = fields.Many2one('ai.agent', string='Backup research agent', config_parameter='resale_ai_product.backup_agent_id')
    resale_ai_default_category_id = fields.Many2one(
        'product.category', string='Default product category',
        config_parameter='resale_ai_product.default_category_id',
        domain="[('category_code', '!=', False)]",
    )
    resale_ai_default_brand_value_id = fields.Many2one(
        'product.attribute.value', string='Default brand',
        config_parameter='resale_ai_product.default_brand_value_id',
        domain="[('attribute_id', '=', brand_attribute_id)]",
    )
