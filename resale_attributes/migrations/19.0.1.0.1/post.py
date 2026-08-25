from odoo import api
from odoo.tools.mail import html2plaintext


def migrate(cr, version):
    env = api.Environment(cr, api.SUPERUSER_ID, {})
    records = env['resale.condition.text'].search([])
    for record in records:
        vals = {}
        for fname in ('operator_text', 'listing_text', 'followup_text'):
            value = record[fname]
            if value and ('<' in value and '>' in value):
                vals[fname] = html2plaintext(value)
        if vals:
            record.write(vals)
