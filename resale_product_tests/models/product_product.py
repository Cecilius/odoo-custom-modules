from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    resale_last_test_result_id = fields.Many2one(
        'resale.product.test.result',
        string='Last Test Result',
        compute='_compute_resale_last_test_result_id',
        store=True,
        readonly=True,
    )

    @api.depends(
        'product_tmpl_id.resale_product_test_ids.test_date',
        'product_tmpl_id.resale_product_test_ids.result_id',
    )
    def _compute_resale_last_test_result_id(self):
        tests = self.env['resale.product.test'].search(
            [('product_template_id', 'in', self.mapped('product_tmpl_id').ids)],
            order='test_date desc, id desc',
        )
        latest_by_template = {}
        for test in tests:
            latest_by_template.setdefault(test.product_template_id.id, test.result_id)
        for product in self:
            product.resale_last_test_result_id = latest_by_template.get(
                product.product_tmpl_id.id,
            )
