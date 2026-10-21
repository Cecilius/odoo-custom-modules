"""Tests for shared platform advertisement links and dynamic platforms."""

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestResaleListing(TransactionCase):
    """Verify platform detection, deduplication, and platform filters."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_a = cls.env['product.template'].create({'name': 'Product A'})
        cls.product_b = cls.env['product.template'].create({'name': 'Product B'})
        cls.ebay = cls.env.ref('resale_advertisements.resale_platform_ebay')
        cls.wallapop = cls.env.ref('resale_advertisements.resale_platform_wallapop')
        cls.vinted = cls.env.ref('resale_advertisements.resale_platform_vinted')

    def _add_listing(self, product, url, platform=False):
        values = {'url': url}
        if platform:
            values['platform_id'] = platform.id
        product.listing_ids = [(0, 0, values)]

    def test_host_keyword_defaults_from_name(self):
        platform = self.env['resale.platform'].create({'name': 'Reverb'})
        self.assertEqual(platform.host_keyword, 'reverb')

    def test_platform_is_inferred_from_url(self):
        self.product_a.new_listing_url = 'https://www.eBay.de/itm/12345'
        self.product_a.action_add_listing()
        self.assertEqual(self.product_a.listing_ids.platform_id, self.ebay)
        self.assertFalse(self.product_a.new_listing_url, 'Input field must be cleared.')

    def test_new_platform_record_is_detected(self):
        self.env['resale.platform'].create({'name': 'Reverb', 'sequence': 5})
        self.product_a.new_listing_url = 'https://reverb.com/item/1'
        self.product_a.action_add_listing()
        self.assertEqual(self.product_a.listing_ids.platform_id.name, 'Reverb')

    def test_unknown_platform_stays_empty(self):
        self.product_a.new_listing_url = 'https://shop.example/item/1'
        self.product_a.action_add_listing()
        self.assertFalse(self.product_a.listing_ids.platform_id)

    def test_add_requires_url(self):
        with self.assertRaises(UserError):
            self.product_a.action_add_listing()

    def test_padded_url_is_normalized(self):
        self._add_listing(self.product_a, '  https://ebay.example/itm/1  ')
        self.assertEqual(self.product_a.listing_ids.url, 'https://ebay.example/itm/1')

    def test_same_link_on_two_products_shares_one_listing(self):
        self._add_listing(self.product_a, 'https://vinted.example/i/42')
        self._add_listing(self.product_b, 'https://vinted.example/i/42')
        self.assertEqual(self.product_a.listing_ids, self.product_b.listing_ids)
        self.assertEqual(self.product_a.listing_ids.product_count, 2)

    def test_pasted_duplicate_reuses_existing_listing(self):
        self._add_listing(self.product_a, 'https://wallapop.example/en/item/7')
        self.product_b.new_listing_url = 'https://wallapop.example/en/item/7'
        self.product_b.action_add_listing()
        self.assertEqual(self.product_a.listing_ids, self.product_b.listing_ids)

    def test_date_listed_defaults_to_today(self):
        self.product_a.new_listing_url = 'https://vinted.example/i/99'
        self.product_a.action_add_listing()
        self.assertTrue(self.product_a.listing_ids.date_listed)

    def test_listing_platform_ids_follow_platform_changes(self):
        self._add_listing(self.product_a, 'https://example-shop/i/1', self.ebay)
        self.assertEqual(self.product_a.listing_platform_ids, self.ebay)
        self.product_a.listing_ids.platform_id = self.vinted
        self.assertEqual(self.product_a.listing_platform_ids, self.vinted)

    def test_platform_search_on_products(self):
        self._add_listing(self.product_a, 'https://ebay.example/itm/2', self.ebay)
        self._add_listing(self.product_b, 'https://vinted.example/i/3', self.vinted)
        ebay_products = self.env['product.template'].search([
            ('listing_platform_ids', 'in', self.ebay.ids),
        ])
        self.assertEqual(ebay_products, self.product_a)
        no_ads_products = self.env['product.template'].search([
            ('listing_ids', '=', False),
        ])
        self.assertNotIn(self.product_a, no_ads_products)

    def test_removing_last_link_deletes_listing(self):
        self.product_a.new_listing_url = 'https://ebay.example/itm/77'
        self.product_a.action_add_listing()
        listing = self.product_a.listing_ids
        self.product_a.listing_ids = [(3, listing.id)]
        self.assertFalse(listing.exists())

    def test_combined_ad_survives_single_unlink(self):
        self.product_a.new_listing_url = 'https://vinted.example/i/55'
        self.product_a.action_add_listing()
        self.product_b.new_listing_url = 'https://vinted.example/i/55'
        self.product_b.action_add_listing()
        listing = self.product_a.listing_ids
        self.assertEqual(listing, self.product_b.listing_ids)
        self.product_a.listing_ids = [(3, listing.id)]
        self.assertTrue(listing.exists())
        self.assertEqual(self.product_b.listing_ids, listing)

    def test_deleting_last_product_deletes_listing(self):
        self.product_a.new_listing_url = 'https://wallapop.example/en/item/88'
        self.product_a.action_add_listing()
        listing = self.product_a.listing_ids
        self.product_a.unlink()
        self.assertFalse(listing.exists())
