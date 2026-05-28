from odoo import _, fields, models


class RepairInvoiceConfirmWizard(models.TransientModel):
    _name = 'repair_helpdesk.invoice_confirm.wizard'
    _description = 'Invoice Confirmation Wizard'

    note = fields.Text(
        string='Warning',
        readonly=True,
        default=lambda self: _(
            'The repair linked to this order is not yet finished.\n'
            'Are you sure you want to create an invoice already?'
        ),
    )
    sale_order_id = fields.Many2one('sale.order', string='Sales Order', required=True, readonly=True)

    def action_confirm(self):
        return self.sale_order_id.with_context(
            repair_helpdesk_force_invoice=True
        ).action_create_invoice()
