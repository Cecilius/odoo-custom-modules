"""Give existing internal users the new Resale / User group.

``base.group_user`` is a ``noupdate`` record, so the ``implied_ids`` link in
``security/resale_security.xml`` is only applied on a fresh install. Apply it
here for databases upgraded from a version without the resale groups.
"""

from odoo import SUPERUSER_ID, Command, api


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref('base.group_user').write({
        'implied_ids': [Command.link(env.ref('resale_base.group_resale_user').id)],
    })
