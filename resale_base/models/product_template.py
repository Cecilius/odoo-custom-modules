import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    reference_retail_price = fields.Monetary(
        string='Reference Retail Price', currency_field='currency_id'
    )
    launch_year = fields.Integer(string='Product Launch Year')

    ean = fields.Char(
        string='EAN',
        index=True,
        help='EAN-8, EAN-13, or EAN-14 barcode with a valid check digit.',
    )
    upc = fields.Char(
        string='UPC',
        index=True,
        help='12-digit UPC-A barcode with a valid check digit.',
    )
    asin = fields.Char(
        string='ASIN',
        index=True,
        help='10-character Amazon Standard Identification Number.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._normalize_identifiers(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._normalize_identifiers(vals)
        return super().write(vals)

    @staticmethod
    def _normalize_identifiers(vals):
        for field_name in ('ean', 'upc', 'asin'):
            if field_name in vals and isinstance(vals[field_name], str):
                vals[field_name] = vals[field_name].strip().upper() or False

    @staticmethod
    def _has_valid_check_digit(value, first_weight):
        digits = [int(digit) for digit in value]
        checksum = sum(
            digit * (first_weight if index % 2 == 0 else 4 - first_weight)
            for index, digit in enumerate(digits[:-1])
        )
        return (10 - checksum % 10) % 10 == digits[-1]

    @api.constrains('ean')
    def _check_ean(self):
        for product in self:
            if product.ean and (
                not product.ean.isdigit()
                or len(product.ean) not in (8, 13, 14)
                or not self._has_valid_check_digit(product.ean, first_weight=1)
            ):
                raise ValidationError(
                    'EAN must be a valid 8, 13, or 14 digit barcode.'
                )

    @api.constrains('upc')
    def _check_upc(self):
        for product in self:
            if product.upc and (
                not product.upc.isdigit()
                or len(product.upc) != 12
                or not self._has_valid_check_digit(product.upc, first_weight=3)
            ):
                raise ValidationError('UPC must be a valid 12 digit UPC-A barcode.')

    @api.constrains('asin')
    def _check_asin(self):
        for product in self:
            if product.asin and not re.fullmatch(r'[A-Z0-9]{10}', product.asin):
                raise ValidationError(
                    'ASIN must contain exactly 10 letters or digits.'
                )
