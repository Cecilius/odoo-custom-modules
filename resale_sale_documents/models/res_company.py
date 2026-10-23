"""Company wording used to mark second-hand items on document lines."""

from odoo import fields, models


class ResCompany(models.Model):
    """Hold the translatable label added when a condition means used goods."""
    _inherit = 'res.company'

    second_hand_text = fields.Char(
        string='Second Hand Item Text',
        translate=True,
        default='Second hand item',
        help='Shown first in the attribute line of sale orders and invoices '
             'when the sold condition counts as a second-hand item. Leave '
             'empty to hide the marker. Edit per language via the Company '
             'form.',
    )
