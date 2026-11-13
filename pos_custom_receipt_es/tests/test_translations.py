from odoo.tests.common import TransactionCase


class TestReceiptAssets(TransactionCase):
    def test_receipt_template_is_in_the_pos_bundle(self):
        paths = [
            path for path, *__ in self.env['ir.asset']._get_asset_paths('point_of_sale._assets_pos', {})
        ]
        self.assertTrue(any(
            path.endswith('pos_custom_receipt_es/static/src/xml/pos_custom_receipt.xml')
            for path in paths
        ))
