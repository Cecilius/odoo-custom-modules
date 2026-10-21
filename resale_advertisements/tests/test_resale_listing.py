"""Tests for shared platform advertisement links and product listing flags."""

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestResaleListing(TransactionCase):
    """Verify platform detection, deduplication, and platform filters."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_a = cls.env['product.template'].create({'name': 'Product A'})
        cls.product_b = cls.env['product.template'].create({'name': 'Product B'})

    def _add_listing(self, product, platform, url):
        product.listing_ids = [(0, 0, {'platform': platform, 'url': url})]

    def test_platform_is_inferred_from_url(self):
        self.product_a.new_listing_url = 'https://www.eBay.de/itm/12345'
        self.product_a.action_add_listing()
        self.assertEqual(self.product_a.listing_ids.platform, 'ebay')
        self.assertFalse(self.product_a.new_listing_url, 'Input field must be cleared.')

    def test_unknown_platform_stays_empty(self):
        self.product_a.new_listing_url = 'https://reverb.example/item/1'
        self.product_a.action_add_listing()
        self.assertFalse(self.product_a.listing_ids.platform)

    def test_add_requires_url(self):
        with self.assertRaises(UserError):
            self.product_a.action_add_listing()

    def test_padded_url_is_normalized(self):
        self._add_listing(self.product_a, 'ebay', '  https://ebay.example/itm/1  ')
        self.assertEqual(self.product_a.listing_ids.url, 'https://ebay.example/itm/1')

    def test_same_link_on_two_products_shares_one_listing(self):
        self._add_listing(self.product_a, 'vinted', 'https://vinted.example/i/42')
        self._add_listing(self.product_b, 'vinted', 'https://vinted.example/i/42')
        self.assertEqual(self.product_a.listing_ids, self.product_b.listing_ids)
        self.assertEqual(self.product_a.listing_ids.product_count, 2)

    def test_pasted_duplicate_reuses_existing_listing(self):
        self._add_listing(self.product_a, 'wallapop', 'https://wallapop.example/en/item/7')
        self.product_b.new_listing_url = 'https://wallapop.example/en/item/7'
        self.product_b.action_add_listing()
        self.assertEqual(self.product_a.listing_ids, self.product_b.listing_ids)

    def test_date_listed_defaults_to_today(self):
        self.product_a.new_listing_url = 'https://vinted.example/i/99'
        self.product_a.action_add_listing()
        self.assertTrue(self.product_a.listing_ids.date_listed)

    def test_existing_url_is_reused_even_if_platform_was_blank(self):
        self._add_listing(self.product_a, False, 'https://reverb.example/item/3')
        self._add_listing(self.product_b, 'vinted', 'https://reverb.example/item/3')
        self.assertEqual(self.product_a.listing_ids, self.product_b.listing_ids)
        self.assertEqual(len(self.product_a.listing_ids), 1)

    def test_platform_flags_support_list_filters(self):
        self._add_listing(self.product_a, 'ebay', 'https://ebay.example/itm/2')
        self.assertFalse(self.product_a.listed_on_vinted)
        self.assertTrue(self.product_a.listed_on_ebay)
        self.assertFalse(self.product_b.listed_on_ebay)
        ebay_products = self.env['product.template'].search([
            ('listed_on_ebay', '=', True),
        ])
        self.assertIn(self.product_a, ebay_products)
        no_ads_products = self.env['product.template'].search([
            ('listing_ids', '=', False),
        ])
        self.assertIn(self.product_b, no_ads_products)
