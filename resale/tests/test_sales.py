# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestResaleSales(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.partner = cls.env['res.partner'].create({'name': 'Customer'})
        cls.category = cls.env['product.category'].create({
            'name': 'Test Category',
            'rfb_prefix': 'TC',
        })
        cls.policy = cls.env['resale.warranty.policy'].create({
            'name': '3 Months',
            'code': '3M',
            'duration_months': 3,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Resale Item',
            'categ_id': cls.category.id,
            'warranty_policy_id': cls.policy.id,
            'list_price': 100.0,
        })
        cls.product.write({'resale_state': 'ready'})
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.env['stock.quant']._update_available_quantity(
            cls.product, cls.stock_location, 1.0
        )

    def test_sale_confirmation_reserves_item(self):
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.product.id,
                    'product_uom_qty': 1.0,
                }),
            ],
        })
        so.action_confirm()
        self.assertEqual(self.product.resale_state, 'reserved')

    def test_delivery_validation_marks_sold_and_sets_warranty(self):
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.product.id,
                    'product_uom_qty': 1.0,
                }),
            ],
        })
        so.action_confirm()
        picking = so.picking_ids.filtered(
            lambda p: p.picking_type_id.code == 'outgoing'
        )
        self.assertTrue(picking)
        picking.action_assign()
        picking.button_validate()
        self.assertEqual(self.product.resale_state, 'sold')
        self.assertTrue(self.product.warranty_start)
        self.assertTrue(self.product.warranty_end)
        self.assertEqual(
            self.product.warranty_end,
            self.product.warranty_start + relativedelta(months=3),
        )
