"""Tests for shared platform advertisement links and product listing flags."""

from odoo.tests.common import TransactionCase


class TestResaleListing(TransactionCase):
    """Verify deduplication, link normalization, and platform filters."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_a = cls.env['product.template'].create({'name': 'Product A'})
        cls.product_b = cls.env['product.template'].create({'name': 'Product B'})

    def _add_listing(self, product, platform, url):
        product.listing_ids = [(0, 0, {'platform': platform, 'url': url})]

    def test_padded_url_is_normalized(self):
        self._add_listing(self.product_a, 'ebay', '  https://ebay.example/itm/1  ')
        self.assertEqual(self.product_a.listing_ids.url, 'https://ebay.example/itm/1')

    def test_same_link_on_two_products_shares_one_listing(self):
        self._add_listing(self.product_a, 'vinted', 'https://vinted.example/i/42')
        self._add_listing(self.product_b, 'vinted', 'https://vinted.example/i/42')
        self.assertEqual(self.product_a.listing_ids, self.product_b.listing_ids)
        self.assertEqual(self.product_a.listing_ids.product_count, 2)

    def test_same_url_on_different_platforms_creates_separate_listings(self):
        self._add_listing(self.product_a, 'ebay', 'https://same.example/ad')
        self._add_listing(self.product_a, 'wallapop', 'https://same.example/ad')
        self.assertEqual(len(self.product_a.listing_ids), 2)

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
