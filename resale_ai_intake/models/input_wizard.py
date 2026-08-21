from odoo import fields, models, _
from odoo.exceptions import UserError


class ResaleAILookupInputWizard(models.TransientModel):
    _name = 'resale.ai.lookup.input.wizard'
    _description = 'Resale AI Lookup Input'

    parent_wizard_id = fields.Many2one('resale.ai.intake.wizard', required=True)
    ean = fields.Char(string='EAN')
    upc = fields.Char(string='UPC')
    asin = fields.Char(string='ASIN')
    search_text = fields.Char(string='Product Description')

    def action_lookup(self):
        self.ensure_one()
        if not self.ean and not self.upc and not self.asin and not self.search_text:
            raise UserError(_('Enter an EAN, UPC, ASIN, product text, or any combination.'))
        return self.parent_wizard_id.action_lookup_from_identifiers(
            self.ean.strip() if self.ean else False,
            self.upc.strip() if self.upc else False,
            self.asin.strip() if self.asin else False,
            self.search_text.strip() if self.search_text else False,
        )
