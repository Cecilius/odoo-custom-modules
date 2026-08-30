"""Regression tests for advertisement wizard defaults and safety checks."""

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestAdvertisementWizardDefaults(TransactionCase):
    """Verify configured limits and translation source-integrity protection."""

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

    def test_translation_refuses_to_apply_when_source_changed(self):
        languages = self.env['res.lang'].search([
            ('active', '=', True), ('code', '!=', self.env.user.lang),
        ], limit=1)
        if not languages:
            self.skipTest('A second active language is required for translation tests.')
        product = self.env['product.template'].create({
            'name': 'Translation source',
            'description_ecommerce': '<p>Current source</p>',
        })
        wizard = self.env['resale.advertisement.translator'].new({
            'product_template_id': product.id,
            'source_lang': self.env.user.lang,
            'target_lang_id': languages.id,
            'translated_terms': '["first", "second"]',
        })
        with self.assertRaises(UserError):
            wizard.action_apply()
