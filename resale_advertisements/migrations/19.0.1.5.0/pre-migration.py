"""Merge advertisement records sharing one URL before the URL-only unique index."""


def _table_exists(cr, table):
    cr.execute("SELECT to_regclass(%s)", (f'public.{table}',))
    return cr.fetchone()[0] is not None


def migrate(cr, version):
    if not _table_exists(cr, 'resale_listing'):
        return
    if not _table_exists(cr, 'product_template_resale_listing_rel'):
        return
    cr.execute("""
        CREATE TEMP TABLE resale_listing_keep AS
        SELECT id, min(id) OVER (PARTITION BY lower(btrim(url))) AS keep_id
        FROM resale_listing
    """)
    cr.execute("""
        INSERT INTO product_template_resale_listing_rel (product_template_id, listing_id)
        SELECT r.product_template_id, k.keep_id
        FROM product_template_resale_listing_rel r
        JOIN resale_listing_keep k ON k.id = r.listing_id
        WHERE k.keep_id <> r.listing_id
          AND NOT EXISTS (
              SELECT 1
              FROM product_template_resale_listing_rel x
              WHERE x.product_template_id = r.product_template_id
                AND x.listing_id = k.keep_id
          )
    """)
    cr.execute("""
        DELETE FROM product_template_resale_listing_rel r
        USING resale_listing_keep k
        WHERE k.id = r.listing_id
          AND k.keep_id <> r.listing_id
    """)
    cr.execute("""
        DELETE FROM resale_listing
        WHERE id IN (SELECT id FROM resale_listing_keep WHERE keep_id <> id)
    """)
