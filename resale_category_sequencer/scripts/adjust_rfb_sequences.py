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

def adjust_rfb_sequences(env, dry_run=True):
    """Call the model implementation from an interactive Odoo shell."""
    results = env['product.category']._adjust_rfb_sequences(dry_run=dry_run)
    for row in results:
        print(
            '[%s] %s: next=%s -> %s%s' % (
                'DRY-RUN' if dry_run else 'APPLIED',
                row['sequence_code'],
                row['current_next'],
                row['target_next'],
                ' (changed)' if row['changed'] else '',
            )
        )
    return results
