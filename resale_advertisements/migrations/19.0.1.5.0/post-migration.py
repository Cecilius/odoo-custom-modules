"""Convert legacy platform selection values into resale.platform records."""

import odoo

LEGACY_NAMES = {
    'ebay': 'eBay',
    'wallapop': 'Wallapop',
    'vinted': 'Vinted',
}


def _column_exists(cr, table, column):
    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
    """, (table, column))
    return cr.fetchone() is not None


def migrate(cr, version):
    if not _column_exists(cr, 'resale_listing', 'platform'):
        return
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    cr.execute("SELECT DISTINCT lower(btrim(platform)) FROM resale_listing WHERE platform IS NOT NULL")
    legacy_values = [row[0] for row in cr.fetchall() if row[0]]
    for value in legacy_values:
        platform = env['resale.platform'].search(
            [('host_keyword', '=ilike', value)], limit=1)
        if not platform:
            platform = env['resale.platform'].search(
                [('name', '=ilike', LEGACY_NAMES.get(value, value))], limit=1)
        if not platform:
            platform = env['resale.platform'].create({
                'name': LEGACY_NAMES.get(value, value),
                'host_keyword': value,
            })
        cr.execute(
            "SELECT id FROM resale_listing WHERE lower(btrim(platform)) = %s AND platform_id IS NULL",
            (value,),
        )
        listing_ids = [row[0] for row in cr.fetchall()]
        if listing_ids:
            env['resale.listing'].browse(listing_ids).write({'platform_id': platform.id})
    cr.execute("ALTER TABLE resale_listing DROP COLUMN platform")
