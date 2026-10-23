"""Second-hand classification of condition values for document lines."""

from odoo import fields, models


class ResaleConditionText(models.Model):
    """Mark whether selling in this condition means a second-hand item."""
    _inherit = 'resale.condition.text'

    is_second_hand = fields.Boolean(
        string='Second Hand Item',
        default=True,
        help='Products sold in this condition are marked as second-hand '
             'items on sale orders and invoices. Untick for new items.',
    )
