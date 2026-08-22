# Part of Odoo. See LICENSE file for full copyright and licensing details.


def migrate(cr, version):
    """Copy the legacy resale_category_id into the standard product categ_id."""
    cr.execute("""
        SELECT DISTINCT pp.product_tmpl_id, pp.resale_category_id
        FROM product_product pp
        WHERE pp.resale_category_id IS NOT NULL
    """)
    for tmpl_id, cat_id in cr.fetchall():
        cr.execute(
            "UPDATE product_template SET categ_id = %s WHERE id = %s",
            (cat_id, tmpl_id),
        )
