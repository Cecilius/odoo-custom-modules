"""Shared resale-product identity, compliance, and identifier validation."""

import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductCompliance(models.Model):
    """A reusable product identity linked to one or more product templates."""
    _name = 'resale.product'
    _table = 'resale_product'
    _description = 'Resale Product'
    _order = 'name, id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _ean_unique = models.UniqueIndex(
        "USING btree (lower(btrim(ean))) WHERE ean IS NOT NULL AND btrim(ean) <> ''",
        'EAN Code must be unique when provided.',
    )
    _upc_unique = models.UniqueIndex(
        "USING btree (lower(btrim(upc))) WHERE upc IS NOT NULL AND btrim(upc) <> ''",
        'UPC Code must be unique when provided.',
    )
    _asin_unique = models.UniqueIndex(
        "USING btree (lower(btrim(asin))) WHERE asin IS NOT NULL AND btrim(asin) <> ''",
        'ASIN must be unique when provided.',
    )

    name = fields.Char(
        string='Name',
        required=True,
        translate=True,
        default='Resale Product',
        tracking=True,
    )
    product_template_ids = fields.One2many(
        'product.template',
        'resale_product_id',
        string='Products',
        help='Product templates representing this shared resale product.',
    )
    category_id = fields.Many2one(
        'product.category',
        string='Product Category',
        ondelete='restrict',
        tracking=True,
    )
    brand_value_id = fields.Many2one(
        'product.attribute.value',
        string='Brand',
        domain=[('attribute_id.name', '=', 'Brand')],
        ondelete='restrict',
        help='Brand value from the Brand product attribute.',
        tracking=True,
    )
    ean = fields.Char(string='EAN Code', tracking=True)
    upc = fields.Char(string='UPC Code', tracking=True)
    asin = fields.Char(string='ASIN', tracking=True)
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
        ondelete='restrict',
        tracking=True,
    )
    reference_retail_price = fields.Monetary(
        string='Reference Price',
        currency_field='currency_id',
        tracking=True,
    )
    reference_retail_price_updated = fields.Date(
        string='Price Updated',
        tracking=True,
    )
    launch_year = fields.Char(string='Launch year', size=4, tracking=True)
    manufacturer_id = fields.Many2one(
        'res.partner',
        string='Manufacturer',
        ondelete='restrict',
        tracking=True,
    )
    eu_responsible_person_id = fields.Many2one(
        'res.partner',
        string='EU Responsible Person',
        ondelete='restrict',
        tracking=True,
    )
    description = fields.Text(string='Product Description', translate=True, tracking=True)
    ce_compliance = fields.Text(string='CE Compliance', translate=True, tracking=True)
    safety_record = fields.Text(string='Safety Record', translate=True, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        """Normalize identifiers and timestamp initial retail-price values."""
        for vals in vals_list:
            self._normalize_identifiers(vals)
            if (
                'reference_retail_price' in vals
                and vals['reference_retail_price'] is not False
                and 'reference_retail_price_updated' not in vals
            ):
                vals['reference_retail_price_updated'] = fields.Date.context_today(self)
        return super().create(vals_list)

    def write(self, vals):
        """Normalize updates and timestamp retail-price changes."""
        self._normalize_identifiers(vals)
        if (
            'reference_retail_price' in vals
            and 'reference_retail_price_updated' not in vals
            and any(record.reference_retail_price != vals['reference_retail_price'] for record in self)
        ):
            vals = dict(vals)
            vals['reference_retail_price_updated'] = fields.Date.context_today(self)
        return super().write(vals)

    def action_create_product(self):
        """Create a product template linked to this resale-product record."""
        self.ensure_one()
        name_translations, _ = self.get_field_translations('name')
        values = {
            'name': self.with_context(lang='en_US').name,
            'resale_product_id': self.id,
        }
        if self.category_id:
            values['categ_id'] = self.category_id.id
        product_model = self.env['product.template']
        if self.brand_value_id and 'brand_value_id' in product_model._fields:
            values['brand_value_id'] = self.brand_value_id.id
        default_warranty_id = self.env['ir.config_parameter'].sudo().get_param(
            'resale_attributes.default_warranty_value_id'
        )
        if default_warranty_id and 'warranty_value_id' in product_model._fields:
            values['warranty_value_id'] = int(default_warranty_id)
        product = product_model.with_context(lang='en_US').create(values)
        for translation in name_translations:
            if (
                translation['lang'] != 'en_US'
                and translation['value']
                and translation['value'] != translation['source']
            ):
                product.with_context(lang=translation['lang']).write({
                    'name': translation['value'],
                })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Product',
            'res_model': 'product.template',
            'res_id': product.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @staticmethod
    def _normalize_identifiers(vals):
        """Canonicalize identifiers before constraints and unique indexes run."""
        for field_name in ('ean', 'upc', 'asin'):
            if field_name in vals and isinstance(vals[field_name], str):
                vals[field_name] = vals[field_name].strip().upper() or False
        if 'launch_year' in vals and vals['launch_year'] is not False:
            vals['launch_year'] = str(vals['launch_year']).strip() or False

    @staticmethod
    def _has_valid_check_digit(value):
        """Validate the checksum used by EAN and UPC identifiers."""
        digits = [int(digit) for digit in value]
        first_weight = 3 if len(value) % 2 == 0 else 1
        checksum = sum(
            digit * (first_weight if index % 2 == 0 else 4 - first_weight)
            for index, digit in enumerate(digits[:-1])
        )
        return (10 - checksum % 10) % 10 == digits[-1]

    @api.constrains('ean')
    def _check_ean(self):
        for record in self:
            if record.ean and (
                not record.ean.isdigit()
                or len(record.ean) not in (8, 13, 14)
                or not self._has_valid_check_digit(record.ean)
            ):
                raise ValidationError(
                    'EAN Code must be a valid 8, 13, or 14 digit barcode.'
                )

    @api.constrains('upc')
    def _check_upc(self):
        for record in self:
            if record.upc and (
                not record.upc.isdigit()
                or len(record.upc) != 12
                or not self._has_valid_check_digit(record.upc)
            ):
                raise ValidationError(
                    'UPC Code must be a valid 12 digit UPC-A barcode.'
                )

    @api.constrains('asin')
    def _check_asin(self):
        for record in self:
            if record.asin and not re.fullmatch(r'[A-Z0-9]{10}', record.asin):
                raise ValidationError(
                    'ASIN must contain exactly 10 letters or digits.'
                )

    @api.constrains('launch_year')
    def _check_launch_year(self):
        for record in self:
            if record.launch_year and not re.fullmatch(r'\d{4}', record.launch_year):
                raise ValidationError('Launch year must contain exactly four digits.')
