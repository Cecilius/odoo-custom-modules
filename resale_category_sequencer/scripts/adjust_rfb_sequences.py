"""Align RFB category sequences with references already in the database.

Run from an Odoo shell::

    exec(open('/mnt/custom-addons/resale_category_sequencer/scripts/'
              'adjust_rfb_sequences.py').read())
    rows = adjust_rfb_sequences(env, dry_run=True)   # inspect changes
    rows = adjust_rfb_sequences(env, dry_run=False)  # apply changes
    env.cr.commit()

The script adjusts only ``ir.sequence.number_next`` and creates missing
category sequences when applying. It never changes product references.
"""

import re


_RFB_REFERENCE = re.compile(r'^RFB-(?P<category>\d{2})-(?P<number>\d+)$')


def _existing_rfb_numbers(env):
    """Return the highest allocated number found for each RFB category code."""
    highest = {}
    products = env['product.template'].search([
        ('default_code', 'ilike', 'RFB-%'),
    ])
    for product in products:
        match = _RFB_REFERENCE.match((product.default_code or '').strip().upper())
        if match:
            category_code = match.group('category')
            number = int(match.group('number'))
            highest[category_code] = max(highest.get(category_code, 0), number)
    return highest


def adjust_rfb_sequences(env, dry_run=True):
    """Align each coded category sequence with existing RFB references.

    :param env: Odoo environment from an ``odoo shell`` session.
    :param bool dry_run: report intended changes without writing anything.
    :return: one result dictionary per coded category.

    A sequence is never moved backwards. This preserves manually advanced
    sequences while preventing reuse of existing references.
    """
    highest = _existing_rfb_numbers(env)
    Category = env['product.category'].sudo()
    Sequence = env['ir.sequence'].sudo()
    results = []

    categories = Category.search(
        [('category_code', '!=', False)],
        order='category_code,id',
    )
    for category in categories:
        code = category.category_code
        sequence_code = f'product.category.seq.{code}'
        sequence = Sequence.search([('code', '=', sequence_code)], limit=1)
        sequence_missing = not sequence
        current_next = sequence.number_next if sequence else 1
        required_next = highest.get(code, 0) + 1
        target_next = max(current_next, required_next)
        changed = not sequence or target_next != current_next

        if changed and not dry_run:
            # Use the module helper so new sequences get standard settings.
            sequence = category._get_or_create_sequence()
            if sequence.number_next != target_next:
                sequence.write({'number_next': target_next})

        results.append({
            'category_id': category.id,
            'category': category.display_name,
            'category_code': code,
            'sequence_code': sequence_code,
            'existing_highest': highest.get(code, 0),
            'current_next': current_next,
            'target_next': target_next,
            'changed': changed,
        })
        print(
            '[%s] %s: next=%s -> %s%s' % (
                'DRY-RUN' if dry_run else 'APPLIED',
                sequence_code,
                current_next,
                target_next,
                ' (created)' if sequence_missing and not dry_run else '',
            )
        )

    return results
