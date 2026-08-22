# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DetailedTest(models.Model):
    _name = 'resale.detailed.test'
    _inherit = ['mail.thread']
    _description = 'Detailed Test'
    _order = 'date desc'

    name = fields.Char(string='Reference', default='New', copy=False)
    product_id = fields.Many2one('product.product', string='Item', required=True,
                                 ondelete='cascade', index=True)
    product_rfb = fields.Char(string='RFB', related='product_id.rfb', readonly=True)
    product_name = fields.Char(string='Product Name', related='product_id.name', readonly=True)
    user_id = fields.Many2one('res.users', string='Tester',
                              default=lambda self: self.env.user, required=True)
    date = fields.Datetime(string='Completion Date', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Completed'),
    ], string='Status', default='draft', tracking=True)

    test_type_id = fields.Many2one('resale.test.type', string='Test Type')
    result = fields.Selection([
        ('pass', 'Test completed - no fault noted'),
        ('fault', 'Test completed - fault found'),
        ('unable', 'Unable to test'),
    ], string='Result', required=True)

    final_condition_id = fields.Many2one('resale.condition', string='Final Condition')
    final_functional_status = fields.Selection([
        ('working', 'Working'),
        ('repairable', 'Not working but easy to repair'),
        ('unknown', 'Unknown'),
        ('uncertain', 'Repair uncertain'),
        ('not_working', 'Not working'),
        ('parts_only', 'Tested for parts only'),
    ], string='Final Functional Status')
    final_disposition = fields.Selection([
        ('pricing', 'Ready for pricing'),
        ('repair', 'Needs repair'),
        ('dismantling', 'Needs dismantling'),
        ('scrap', 'Scrap'),
        ('hold', 'Hold'),
    ], string='Final Disposition', required=True)

    comment = fields.Text(string='Comment')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'resale.detailed.test') or 'New'
        return super().create(vals_list)

    def _state_from_disposition(self):
        self.ensure_one()
        return {
            'pricing': 'ready',
            'repair': 'needs_repair',
            'dismantling': 'needs_dismantling',
            'scrap': 'scrapped',
            'hold': 'hold',
        }.get(self.final_disposition, 'inspecting')

    def action_complete(self):
        for test in self:
            if test.state == 'done':
                continue
            if not test.result:
                raise UserError(_('Please select a test result.'))
            if not test.final_disposition:
                raise UserError(_('Please select a final disposition.'))
            item_vals = {
                'condition_id': test.final_condition_id.id,
                'functional_status': test.final_functional_status,
                'resale_state': test._state_from_disposition(),
            }
            if test.final_condition_id and test.final_condition_id.warranty_policy_id and not test.product_id.warranty_policy_id:
                item_vals['warranty_policy_id'] = test.final_condition_id.warranty_policy_id.id
            if test.final_condition_id:
                item_vals['condition_factor'] = test.final_condition_id.condition_factor
            test.product_id.write(item_vals)
            test.product_id._sync_condition_grade_from_condition()
            test.write({
                'state': 'done',
                'date': fields.Datetime.now(),
            })
        return True
