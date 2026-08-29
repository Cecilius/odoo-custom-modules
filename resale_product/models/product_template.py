from odoo import api, fields, models


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
        string='Product Category',
        readonly=True,
    )
    resale_product_brand_value_id = fields.Many2one(
        related='resale_product_id.brand_value_id',
        string='Product Brand',
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
        string='Product Currency',
        readonly=True,
    )
    resale_product_description = fields.Text(
        related='resale_product_id.description',
        string='Prod. Description',
        readonly=True,
    )
    resale_product_manufacturer_id = fields.Many2one(
        related='resale_product_id.manufacturer_id',
        string='Manufacturer',
        readonly=False,
    )
    resale_product_eu_responsible_person_id = fields.Many2one(
        related='resale_product_id.eu_responsible_person_id',
        string='EU Resp. Person',
        readonly=False,
    )
    resale_product_ce_compliance = fields.Text(
        related='resale_product_id.ce_compliance',
        string='CE Compliance',
        readonly=False,
    )
    resale_product_safety_record = fields.Text(
        related='resale_product_id.safety_record',
        string='Safety Record',
        readonly=False,
    )
    manufacturer_contact_copy = fields.Text(
        string='Manufacturer:',
        compute='_compute_gpsr_contact_copy',
        help='Manufacturer contact details (single line) for copy/paste.',
    )
    eu_responsible_contact_copy = fields.Text(
        string='EU Resp. Person:',
        compute='_compute_gpsr_contact_copy',
        help='EU Responsible Person contact details (single line) for copy/paste.',
    )

    @api.depends(
        'resale_product_manufacturer_id',
        'resale_product_manufacturer_id.name', 'resale_product_manufacturer_id.street',
        'resale_product_manufacturer_id.street2', 'resale_product_manufacturer_id.city',
        'resale_product_manufacturer_id.zip', 'resale_product_manufacturer_id.state_id',
        'resale_product_manufacturer_id.country_id', 'resale_product_manufacturer_id.email',
        'resale_product_manufacturer_id.phone', 'resale_product_manufacturer_id.website',
        'resale_product_eu_responsible_person_id',
        'resale_product_eu_responsible_person_id.name', 'resale_product_eu_responsible_person_id.street',
        'resale_product_eu_responsible_person_id.street2', 'resale_product_eu_responsible_person_id.city',
        'resale_product_eu_responsible_person_id.zip', 'resale_product_eu_responsible_person_id.state_id',
        'resale_product_eu_responsible_person_id.country_id', 'resale_product_eu_responsible_person_id.email',
        'resale_product_eu_responsible_person_id.phone', 'resale_product_eu_responsible_person_id.website',
    )
    def _compute_gpsr_contact_copy(self):
        for record in self:
            record.manufacturer_contact_copy = self._format_contact_line(record.resale_product_manufacturer_id)
            record.eu_responsible_contact_copy = self._format_contact_line(record.resale_product_eu_responsible_person_id)

    def _format_contact_line(self, partner):
        if not partner:
            return ''
        parts = []
        if partner.name:
            parts.append(partner.name)
        if partner.street:
            parts.append(partner.street)
        if partner.street2:
            parts.append(partner.street2)
        if partner.zip or partner.city:
            parts.append(' '.join(p for p in (partner.zip, partner.city) if p))
        if partner.state_id:
            parts.append(partner.state_id.name or '')
        if partner.country_id:
            parts.append(partner.country_id.name or '')
        if partner.email:
            parts.append('Email: %s' % partner.email)
        if partner.phone:
            parts.append('Phone: %s' % partner.phone)
        if partner.website:
            parts.append('Web: %s' % partner.website)
        return ', '.join(p for p in parts if p)
