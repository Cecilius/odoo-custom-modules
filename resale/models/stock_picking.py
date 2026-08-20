# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta

from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    resale_batch_id = fields.Many2one(
        'resale.acquisition.batch',
        string='Resale Batch',
        copy=False,
        index=True,
    )

    def _action_done(self):
        res = super()._action_done()
        for picking in self:
            if picking.picking_type_id.code == 'incoming':
                returned_products = picking.move_ids.filtered(
                    'origin_returned_move_id'
                ).mapped('product_id').filtered('rfb')
                for product in returned_products:
                    product.write({
                        'resale_state': 'inspecting',
                        'eval_done': False,
                        'eval_date': False,
                        'eval_user_id': False,
                        'warranty_start': False,
                        'warranty_end': False,
                    })
                continue
            if picking.picking_type_id.code != 'outgoing':
                continue
            done_date = (
                picking.date_done.date()
                if picking.date_done
                else fields.Date.context_today(picking)
            )
            products = picking.move_line_ids.mapped('product_id')
            for product in products:
                if not product.rfb or product.resale_state == 'sold':
                    continue
                if product.resale_state not in ('reserved', 'ready', 'published'):
                    continue
                vals = {'resale_state': 'sold'}
                policy = product.warranty_policy_id
                if policy and policy.duration_months:
                    vals['warranty_start'] = done_date
                    vals['warranty_end'] = (
                        done_date + relativedelta(months=policy.duration_months)
                    )
                product.write(vals)
        return res
