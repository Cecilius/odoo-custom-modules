"""One-time backfills for the line-description revamp (19.0.1.4.0)."""

from odoo import api


def migrate(cr, version):
    env = api.Environment(cr, api.SUPERUSER_ID, {})
    # Describe Condition and Warranty on lines; keep others hidden until ticked.
    for xmlid in (
        'resale_attributes.product_attribute_condition',
        'resale_attributes.product_attribute_warranty',
    ):
        env.ref(xmlid).write({'resale_show_on_lines': True})
    # Every existing condition mapping counts as second-hand until unticked.
    env['resale.condition.text'].search([('is_second_hand', '=', False)]) \
        .write({'is_second_hand': True})
    # Give companies created before this version the default marker wording.
    env['res.company'].search([('second_hand_text', '=', False)]) \
        .write({'second_hand_text': 'Second hand item'})
    env.flush_all()
