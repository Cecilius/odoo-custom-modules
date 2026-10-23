"""Install-time backfills for the document line description features."""


def post_init_hook(env):
    # Describe Condition and Warranty on lines; keep others hidden until ticked.
    for xmlid in (
        'resale_attributes.product_attribute_condition',
        'resale_attributes.product_attribute_warranty',
    ):
        attribute = env.ref(xmlid, raise_if_not_found=False)
        if attribute:
            attribute.write({'resale_show_on_lines': True})
    # Every existing condition mapping counts as second-hand until unticked.
    env['resale.condition.text'].search([('is_second_hand', '=', False)]) \
        .write({'is_second_hand': True})
    # Give companies created before this version the default marker wording.
    env['res.company'].search([('second_hand_text', '=', False)]) \
        .write({'second_hand_text': 'Second hand item'})
    env.flush_all()
