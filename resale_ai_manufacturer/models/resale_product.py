"""Expose GPSR research from reusable resale-product records."""

from odoo import _, models


class ResaleProduct(models.Model):
    """Open manufacturer research directly from a resale-product record."""
    _inherit = 'resale.product'

    def action_find_gpsr_info(self):
        """Open the GPSR manufacturer and EU-responsible-person wizard."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Find GPSR Compliance Info'),
            'res_model': 'resale.ai.manufacturer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_resale_product_id': self.id},
        }
