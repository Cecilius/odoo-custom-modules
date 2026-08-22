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
        test_model = self.env['resale.product.test']
        for product in self:
            latest_test = test_model.search(
                [('product_template_id', '=', product.product_tmpl_id.id)],
                order='test_date desc, id desc',
                limit=1,
            )
            product.resale_last_test_result_id = latest_test.result_id
