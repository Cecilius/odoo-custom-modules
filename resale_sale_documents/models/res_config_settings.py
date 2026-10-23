"""Settings for the second-hand marker shown on document lines."""

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Expose the company-level second-hand marker wording."""
    _inherit = 'res.config.settings'

    second_hand_text = fields.Char(
        related='company_id.second_hand_text', readonly=False,
    )
