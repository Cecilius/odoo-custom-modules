from odoo import _, models


class ResaleProduct(models.Model):
    _inherit = 'resale.product'

    def action_find_gpsr_info(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Find GPSR Compliance Info'),
            'res_model': 'resale.ai.manufacturer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_resale_product_id': self.id},
        }
