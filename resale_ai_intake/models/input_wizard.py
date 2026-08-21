from odoo import fields, models, _
from odoo.exceptions import UserError


class ResaleAILookupInputWizard(models.TransientModel):
    _name = 'resale.ai.lookup.input.wizard'
    _description = 'Resale AI Lookup Input'

    parent_wizard_id = fields.Many2one('resale.ai.intake.wizard', required=True)
    ean = fields.Char(string='EAN / UPC')
    asin = fields.Char(string='ASIN')

    def action_lookup(self):
        self.ensure_one()
        if not self.ean and not self.asin:
            raise UserError(_('Enter an EAN/UPC, an ASIN, or both.'))
        return self.parent_wizard_id.action_lookup_from_identifiers(
            self.ean.strip() if self.ean else False,
            self.asin.strip() if self.asin else False,
        )
