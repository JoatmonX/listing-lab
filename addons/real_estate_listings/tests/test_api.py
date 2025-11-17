import json

from odoo.tests.common import HttpCase, SavepointCase


class TestRealEstateAPI(HttpCase):
    """Test the Real Estate API endpoints"""

    def setUp(self):
        super(TestRealEstateAPI, self).setUp()
        # Create a test user with appropriate permissions
        self.test_user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'test_user',
            'password': 'test_password',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])]
        })

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

        # Create a test photo
        self.test_photo = self.env['real_estate.photo'].create({
            'listing_id': self.test_listing.id,
            'url': 'https://example.com/test.jpg',
            'is_primary': True,
            'sequence': 1
        })

        # Create a test popularity record
        self.test_popularity = self.env['real_estate.popularity'].create({
            'listing_id': self.test_listing.id,
            'last_n_days': 7,
            'views_total': 100,
            'saves_total': 10,
            'shares_total': 5,
            'clicks_total': 20
        })

        # Create a test tax history record
        self.test_tax_history = self.env['real_estate.property.tax.history'].create({
            'listing_id': self.test_listing.id,
            'year': 2024,
            'tax_amount': 3000,
            'assessment': 200000
        })

        # Authentication headers
        self.headers = {
            'Content-Type': 'application/json',
        }

    def test_get_listings(self):
        """Test the GET /api/real_estate/listings endpoint"""
        response = self.url_open('/api/real_estate/listings')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['status'], 'success')
        self.assertTrue(isinstance(data['data'], list))

        # Check if our test listing is in the response
        found = False
        for listing in data['data']:
            if listing['property_id'] == 'TEST123':
                found = True
                self.assertEqual(listing['listing_id'], 'TEST-LIST-123')
                self.assertEqual(listing['bedrooms'], 3)
                self.assertEqual(listing['baths_full'], 2)
                self.assertEqual(listing['sqft'], 1800)
                self.assertEqual(listing['property_type'], 'single_family')
                self.assertEqual(listing['photo_count'], 1)
                break

        self.assertTrue(found, "Test listing not found in response")

    def test_get_listing(self):
        """Test the GET /api/real_estate/listings/<id> endpoint"""
        response = self.url_open(f'/api/real_estate/listings/{self.test_listing.id}')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['status'], 'success')

        listing = data['data']
        self.assertEqual(listing['property_id'], 'TEST123')
        self.assertEqual(listing['listing_id'], 'TEST-LIST-123')
        self.assertEqual(listing['price'], 250000)
        self.assertEqual(listing['bedrooms'], 3)
        self.assertEqual(listing['baths_full'], 2)
        self.assertEqual(listing['sqft'], 1800)
        self.assertEqual(listing['property_type'], 'single_family')

        # Check address
        self.assertEqual(listing['address']['street'], '123 Test St')
        self.assertEqual(listing['address']['city'], 'Test City')
        self.assertEqual(listing['address']['state'], 'TS')
        self.assertEqual(listing['address']['zip_code'], '12345')

        # Check photos
        self.assertEqual(len(listing['photos']), 1)
        self.assertEqual(listing['photos'][0]['url'], 'https://example.com/test.jpg')
        self.assertTrue(listing['photos'][0]['is_primary'])

        # Check popularity
        self.assertEqual(len(listing['popularity']), 1)
        self.assertEqual(listing['popularity'][0]['last_n_days'], 7)
        self.assertEqual(listing['popularity'][0]['views_total'], 100)

        # Check tax history
        self.assertEqual(len(listing['tax_history']), 1)
        self.assertEqual(listing['tax_history'][0]['year'], 2024)
        self.assertEqual(listing['tax_history'][0]['tax_amount'], 3000)

    def test_get_listing_not_found(self):
        """Test the GET /api/real_estate/listings/<id> endpoint with invalid ID"""
        response = self.url_open('/api/real_estate/listings/999999')
        self.assertEqual(response.status_code, 404)

        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['message'], 'Listing not found')

    def test_create_listing(self):
        """Test the POST /api/real_estate/listings endpoint"""
        # Login as test user
        self.authenticate('test_user', 'test_password')

        # Prepare test data
        test_data = {
            'property_id': 'TEST456',
            'listing_id': 'TEST-LIST-456',
            'price': 350000,
            'bedrooms': 4,
            'baths_full': 3,
            'sqft': 2200,
            'lot_sqft': 12000,
            'property_type': 'single_family',
            'address': {
                'street': '456 Test Ave',
                'city': 'Test Town',
                'state': 'TS',
                'zip_code': '54321'
            },
            'year_built': 2010,
            'photos': [
                {
                    'url': 'https://example.com/test2.jpg',
                    'is_primary': True,
                    'sequence': 1,
                    'tags': ['exterior', 'front']
                }
            ],
            'popularity': [
                {
                    'last_n_days': 7,
                    'views_total': 50,
                    'saves_total': 5,
                    'shares_total': 2,
                    'clicks_total': 10
                }
            ],
            'tax_history': [
                {
                    'year': 2024,
                    'tax_amount': 4000,
                    'assessment': 300000
                }
            ]
        }

        response = self.url_open(
            '/api/real_estate/listings',
            data=json.dumps(test_data).encode(),
            headers=self.headers,
            method='POST'
        )

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['status'], 'success')

        # Verify the listing was created
        created_listing_id = data['data']['id']
        created_listing = self.env['real_estate.listing'].browse(created_listing_id)

        self.assertEqual(created_listing.property_id, 'TEST456')
        self.assertEqual(created_listing.listing_id, 'TEST-LIST-456')
        self.assertEqual(created_listing.price, 350000)
        self.assertEqual(created_listing.bedrooms, 4)
        self.assertEqual(created_listing.street, '456 Test Ave')

        # Check that related records were created
        self.assertEqual(len(created_listing.photo_ids), 1)
        self.assertEqual(len(created_listing.popularity_ids), 1)
        self.assertEqual(len(created_listing.tax_history_ids), 1)

    def test_update_listing(self):
        """Test the PUT /api/real_estate/listings/<id> endpoint"""
        # Login as test user
        self.authenticate('test_user', 'test_password')

        # Prepare update data
        update_data = {
            'price': 275000,
            'bedrooms': 4,
            'address': {
                'street': '123 Updated St',
                'city': 'Updated City'
            }
        }

        response = self.url_open(
            f'/api/real_estate/listings/{self.test_listing.id}',
            data=json.dumps(update_data).encode(),
            headers=self.headers,
            method='PUT'
        )

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['status'], 'success')

        # Verify the listing was updated
        updated_listing = self.env['real_estate.listing'].browse(self.test_listing.id)
        self.assertEqual(updated_listing.price, 275000)
        self.assertEqual(updated_listing.bedrooms, 4)
        self.assertEqual(updated_listing.street, '123 Updated St')
        self.assertEqual(updated_listing.city, 'Updated City')

        # Other fields should remain unchanged
        self.assertEqual(updated_listing.property_id, 'TEST123')
        self.assertEqual(updated_listing.baths_full, 2)

    def test_delete_listing(self):
        """Test the DELETE /api/real_estate/listings/<id> endpoint"""
        # Login as test user
        self.authenticate('test_user', 'test_password')

        # Create a listing to delete
        listing_to_delete = self.env['real_estate.listing'].create({
            'property_id': 'DELETE-TEST',
            'listing_id': 'DELETE-LIST-123',
            'price': 200000
        })

        response = self.url_open(
            f'/api/real_estate/listings/{listing_to_delete.id}',
            headers=self.headers,
            method='DELETE'
        )

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['status'], 'success')

        # Verify the listing was deleted
        deleted_listing = self.env['real_estate.listing'].browse(listing_to_delete.id)
        self.assertFalse(deleted_listing.exists())

    def test_get_photos(self):
        """Test the GET /api/real_estate/photos endpoint"""
        response = self.url_open('/api/real_estate/photos')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['status'], 'success')
        self.assertTrue(isinstance(data['data'], list))

        # Check if our test photo is in the response
        found = False
        for photo in data['data']:
            if photo['url'] == 'https://example.com/test.jpg':
                found = True
                self.assertEqual(photo['listing_id'], self.test_listing.id)
                self.assertTrue(photo['is_primary'])
                break

        self.assertTrue(found, "Test photo not found in response")

    def test_get_popularity(self):
        """Test the GET /api/real_estate/popularity endpoint"""
        response = self.url_open('/api/real_estate/popularity')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['status'], 'success')
        self.assertTrue(isinstance(data['data'], list))

        # Check if our test popularity record is in the response
        found = False
        for pop in data['data']:
            if pop['listing_id'] == self.test_listing.id and pop['last_n_days'] == 7:
                found = True
                self.assertEqual(pop['views_total'], 100)
                self.assertEqual(pop['saves_total'], 10)
                self.assertEqual(pop['shares_total'], 5)
                self.assertEqual(pop['clicks_total'], 20)
                break

        self.assertTrue(found, "Test popularity record not found in response")
