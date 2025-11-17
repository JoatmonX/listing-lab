import json

from odoo.tests.common import TransactionCase


class TestRealEstateJSON2API(TransactionCase):
    """Test the Real Estate JSON-2 API endpoints"""

    def setUp(self):
        super(TestRealEstateJSON2API, self).setUp()
        
        # Create test data
        self.test_listing = self.env['real_estate.listing'].create({
            'property_id': 'TEST123',
            'listing_id': 'TEST-LIST-123',
            'price': 250000,
            'bedrooms': 3,
            'baths_full': 2,
            'sqft': 1800,
            'lot_sqft': 10000,
            'property_type': 'single_family',
            'street': '123 Test St',
            'city': 'Test City',
            'state': 'TS',
            'zip_code': '12345',
            'year_built': 2000
        })

    def test_json2_api_methods(self):
        """Test the JSON-2 API methods directly"""
        # Test search method
        controller = self.env['ir.http']._get_controller_for_route('/json/2/real_estate.listing/search')
        self.assertTrue(controller, "Controller for /json/2/real_estate.listing/search not found")
        
        # Test read method
        controller = self.env['ir.http']._get_controller_for_route('/json/2/real_estate.listing/read')
        self.assertTrue(controller, "Controller for /json/2/real_estate.listing/read not found")
        
        # Test search_read method
        controller = self.env['ir.http']._get_controller_for_route('/json/2/real_estate.listing/search_read')
        self.assertTrue(controller, "Controller for /json/2/real_estate.listing/search_read not found")
        
        # Test create method
        controller = self.env['ir.http']._get_controller_for_route('/json/2/real_estate.listing/create')
        self.assertTrue(controller, "Controller for /json/2/real_estate.listing/create not found")