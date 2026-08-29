from odoo.tests.common import TransactionCase


class TestAdvertisementWizardDefaults(TransactionCase):

    def test_long_listing_uses_configured_max_characters(self):
        self.env['ir.config_parameter'].sudo().set_param(
            'resale_advertisement.max_characters', '777'
        )
        defaults = self.env['resale.advertisement.generator'].default_get([
            'max_characters',
        ])
        self.assertEqual(defaults['max_characters'], 777)

    def test_short_listing_uses_configured_max_characters(self):
        self.env['ir.config_parameter'].sudo().set_param(
            'resale_advertisement.short_max_characters', '88'
        )
        defaults = self.env['resale.advertisement.short_generator'].default_get([
            'max_characters',
        ])
        self.assertEqual(defaults['max_characters'], 88)
