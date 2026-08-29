from odoo import _, models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def action_find_gpsr_info(self):
        self.ensure_one()
        if not self.resale_product_id:
            raise UserError(_(
                'This product is not linked to a Resale Product. '
                'Please assign a Resale Product first before running the GPSR research.'
            ))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Find GPSR Compliance Info'),
            'res_model': 'resale.ai.manufacturer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_resale_product_id': self.resale_product_id.id},
        }
