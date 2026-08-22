from odoo import fields, models, _
from odoo.exceptions import UserError


class ResaleAIResearchWizard(models.TransientModel):
    _name = 'resale.ai.research.wizard'
    _description = 'Resale AI Research Fields'

    parent_wizard_id = fields.Many2one('resale.ai.intake.wizard', required=True)
    role = fields.Selection([
        ('deep', 'Deep Research'),
        ('secondary', 'Secondary Matching'),
    ], default='deep', required=True)
    research_name = fields.Boolean(string='Name', default=True)
    research_model = fields.Boolean(string='Model')
    research_brand = fields.Boolean(string='Brand')
    research_category = fields.Boolean(string='Category')
    research_asin = fields.Boolean(string='ASIN')
    research_ean = fields.Boolean(string='EAN')
    research_upc = fields.Boolean(string='UPC')
    research_current_price = fields.Boolean(string='Current Price')
    research_lowest_price_180 = fields.Boolean(string='Lowest Price (180 days)')

    def action_research(self):
        self.ensure_one()
        fields_to_update = [
            field_name for field_name, enabled in (
                ('name', self.research_name),
                ('model', self.research_model),
                ('brand', self.research_brand),
                ('category', self.research_category),
                ('asin', self.research_asin),
                ('ean', self.research_ean),
                ('upc', self.research_upc),
                ('current_price', self.research_current_price),
                ('lowest_price_180', self.research_lowest_price_180),
            ) if enabled
        ]
        if not fields_to_update:
            raise UserError(_('Select at least one field to research.'))
        return self.parent_wizard_id.action_research_selected(
            fields_to_update,
            self.role,
        )
