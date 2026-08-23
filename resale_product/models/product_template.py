from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    resale_product_id = fields.Many2one(
        'resale.product',
        string='Resale Product',
        ondelete='set null',
        index=True,
    )
    resale_product_ean = fields.Char(related='resale_product_id.ean', readonly=True)
    resale_product_upc = fields.Char(related='resale_product_id.upc', readonly=True)
    resale_product_asin = fields.Char(related='resale_product_id.asin', readonly=True)
    resale_product_launch_year = fields.Char(
        related='resale_product_id.launch_year',
        string='Launch year',
        readonly=True,
    )
    resale_product_category_id = fields.Many2one(
        related='resale_product_id.category_id',
        string='Resale Product Category',
        readonly=True,
    )
    resale_product_brand_value_id = fields.Many2one(
        related='resale_product_id.brand_value_id',
        string='Resale Product Brand',
        readonly=True,
    )
    resale_product_reference_price = fields.Monetary(
        related='resale_product_id.reference_retail_price',
        string='Reference Price',
        currency_field='resale_product_currency_id',
        readonly=True,
    )
    resale_product_currency_id = fields.Many2one(
        'res.currency',
        related='resale_product_id.currency_id',
        string='Resale Product Currency',
        readonly=True,
    )
    resale_product_description = fields.Text(
        related='resale_product_id.description',
        string='Resale Product Description',
        readonly=True,
    )
    resale_product_manufacturer_id = fields.Many2one(
        related='resale_product_id.manufacturer_id',
        string='Resale Product Manufacturer',
        readonly=True,
    )
    resale_product_eu_responsible_person_id = fields.Many2one(
        related='resale_product_id.eu_responsible_person_id',
        string='Resale Product EU Responsible Person',
        readonly=True,
    )
    resale_product_ce_compliance = fields.Text(
        related='resale_product_id.ce_compliance',
        string='Resale Product CE Compliance',
        readonly=True,
    )
    resale_product_safety_record = fields.Text(
        related='resale_product_id.safety_record',
        string='Resale Product Safety Record',
        readonly=True,
    )
