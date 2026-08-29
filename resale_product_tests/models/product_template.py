"""Expose the most recent operator test result on product templates."""

from odoo import api, fields, models


class ProductTemplate(models.Model):
    """Link product templates to their chronological operator test records."""
    _inherit = 'product.template'

    resale_last_test_result_id = fields.Many2one(
        'resale.product.test.result',
        string='Last Test Result',
        compute='_compute_resale_last_test_result_id',
        readonly=True,
    )
    resale_product_test_ids = fields.One2many(
        'resale.product.test',
        'product_template_id',
        string='Product Tests',
    )

    @api.depends('resale_product_test_ids.test_date', 'resale_product_test_ids.result_id')
    def _compute_resale_last_test_result_id(self):
        """Use the model's date/id ordering to select the latest test result."""
        for product in self:
            latest_test = product.resale_product_test_ids[:1]
            product.resale_last_test_result_id = latest_test.result_id
