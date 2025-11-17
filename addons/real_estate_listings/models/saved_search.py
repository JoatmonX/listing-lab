import json
import logging
import os

import pika
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class RealEstateSavedSearch(models.Model):
    _name = 'real_estate.saved_search'
    _description = 'Real Estate Saved Searches'
    _rec_name = 'name'

    # Basic Information
    name = fields.Char(string='Search Name', required=True, help='Name for this saved search')

    # Required Fields
    location = fields.Char(
        string='Location',
        required=True,
        help='Flexible location search - accepts ZIP code, City, City/State, Full address, Neighborhood, or County'
    )
    listing_type = fields.Selection([
        ('for_rent', 'For Rent'),
        ('for_sale', 'For Sale'),
        ('sold', 'Sold'),
        ('pending', 'Pending/Contingent')
    ], string='Listing Type', required=True, default='for_sale', help='Type of listing to search for')

    # Optional Fields - Property Type
    property_type_ids = fields.Many2many(
        'real_estate.saved_search.property_type',
        relation='re_saved_search_property_type_rel',
        string='Property Types',
        help='Types of properties to include in search'
    )

    # Optional Fields - Search Radius
    radius = fields.Float(
        string='Radius (miles)',
        help='Radius in miles to find comparable properties based on individual addresses'
    )

    # Optional Fields - Time Filters
    past_days = fields.Integer(
        string='Past Days',
        help='Number of past days to filter properties'
    )
    past_hours = fields.Integer(
        string='Past Hours',
        help='Number of past hours to filter properties (more precise than past_days)'
    )
    date_from = fields.Date(
        string='Date From',
        help='Start date to filter properties listed or sold (YYYY-MM-DD)'
    )
    date_to = fields.Date(
        string='Date To',
        help='End date to filter properties listed or sold (YYYY-MM-DD)'
    )
    datetime_from = fields.Datetime(
        string='Datetime From',
        help='Start datetime for hour-precise filtering (YYYY-MM-DDTHH:MM:SS)'
    )
    datetime_to = fields.Datetime(
        string='Datetime To',
        help='End datetime for hour-precise filtering (YYYY-MM-DDTHH:MM:SS)'
    )

    # Optional Fields - Property Characteristics
    beds_min = fields.Integer(string='Min Bedrooms', help='Minimum number of bedrooms')
    beds_max = fields.Integer(string='Max Bedrooms', help='Maximum number of bedrooms')
    baths_min = fields.Float(string='Min Bathrooms', help='Minimum number of bathrooms')
    baths_max = fields.Float(string='Max Bathrooms', help='Maximum number of bathrooms')
    sqft_min = fields.Integer(string='Min Square Feet', help='Minimum square footage')
    sqft_max = fields.Integer(string='Max Square Feet', help='Maximum square footage')
    # Currency for price filters
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        help='Currency for price filters'
    )

    price_min = fields.Monetary(string='Min Price', currency_field='currency_id', help='Minimum listing price')
    price_max = fields.Monetary(string='Max Price', currency_field='currency_id', help='Maximum listing price')
    lot_sqft_min = fields.Integer(string='Min Lot Size (sqft)', help='Minimum lot size in square feet')
    lot_sqft_max = fields.Integer(string='Max Lot Size (sqft)', help='Maximum lot size in square feet')
    year_built_min = fields.Integer(string='Min Year Built', help='Minimum year built')
    year_built_max = fields.Integer(string='Max Year Built', help='Maximum year built')

    # Optional Fields - Sorting
    sort_by = fields.Selection([
        ('list_date', 'List Date'),
        ('sold_date', 'Sold Date'),
        ('list_price', 'List Price'),
        ('sqft', 'Square Feet'),
        ('beds', 'Bedrooms'),
        ('baths', 'Bathrooms')
    ], string='Sort By', help='Field to sort results by')
    sort_direction = fields.Selection([
        ('asc', 'Ascending'),
        ('desc', 'Descending')
    ], string='Sort Direction', default='desc', help='Sort direction')

    # Optional Fields - Flags
    mls_only = fields.Boolean(string='MLS Only', help='Fetch only MLS listings')
    foreclosure = fields.Boolean(string='Foreclosure Only', help='Fetch only foreclosures')
    extra_property_data = fields.Boolean(
        string='Extra Property Data',
        help='Fetch additional property data (schools, tax appraisals, etc.)'
    )
    exclude_pending = fields.Boolean(
        string='Exclude Pending',
        help='Exclude pending properties from for_sale results'
    )

    # Optional Fields - Other
    proxy = fields.Char(string='Proxy', help='Proxy in format http://user:pass@host:port')
    limit = fields.Integer(string='Limit', default=10000, help='Limit the number of properties to fetch (max 10000)')

    # Computed fields
    property_type_list = fields.Char(compute='_compute_property_type_list', store=True)

    @api.depends('property_type_ids')
    def _compute_property_type_list(self):
        """Compute a comma-separated list of property types for display purposes"""
        for record in self:
            if record.property_type_ids:
                record.property_type_list = ', '.join(record.property_type_ids.mapped('name'))
            else:
                record.property_type_list = 'All'

    def action_run_search(self):
        """
        Publish a message to RabbitMQ to trigger property scraping based on saved search
        """
        self.ensure_one()

        # Check if we have a location to search
        if not self.location:
            raise UserError("Location is required for property search.")

        _logger.info(f'Publishing search request for: {self.name}')

        try:
            # Get RabbitMQ connection parameters from environment variables
            rabbitmq_host = os.environ.get('RABBITMQ_HOST', 'rabbitmq')
            rabbitmq_port = int(os.environ.get('RABBITMQ_PORT', 5672))
            rabbitmq_user = os.environ.get('RABBITMQ_USER', 'guest')
            rabbitmq_pass = os.environ.get('RABBITMQ_PASS', 'guest')
            rabbitmq_exchange = os.environ.get('RABBITMQ_EXCHANGE', 'property_exchange')
            rabbitmq_routing_key = os.environ.get('RABBITMQ_ROUTING_KEY', 'property.scrape')

            # Prepare message payload
            message = {
                'location': self.location,
                'listing_type': self.listing_type,
            }

            # Add property types if specified
            if self.property_type_ids:
                message['property_type'] = self.property_type_ids.mapped('code')

            if self.radius:
                message['radius'] = self.radius

            # Time filters - ensure we don't mix incompatible filters
            if self.past_days:
                message['past_days'] = self.past_days
            elif self.past_hours:
                message['past_hours'] = self.past_hours
            elif self.date_from and self.date_to:
                message['date_from'] = self.date_from.strftime('%Y-%m-%d')
                message['date_to'] = self.date_to.strftime('%Y-%m-%d')
            elif self.datetime_from and self.datetime_to:
                message['datetime_from'] = self.datetime_from.strftime('%Y-%m-%dT%H:%M:%S')
                message['datetime_to'] = self.datetime_to.strftime('%Y-%m-%dT%H:%M:%S')

            # Property characteristics
            if self.beds_min:
                message['beds_min'] = self.beds_min
            if self.beds_max:
                message['beds_max'] = self.beds_max
            if self.baths_min:
                message['baths_min'] = self.baths_min
            if self.baths_max:
                message['baths_max'] = self.baths_max
            if self.sqft_min:
                message['sqft_min'] = self.sqft_min
            if self.sqft_max:
                message['sqft_max'] = self.sqft_max
            if self.price_min:
                message['price_min'] = self.price_min
            if self.price_max:
                message['price_max'] = self.price_max
            if self.lot_sqft_min:
                message['lot_sqft_min'] = self.lot_sqft_min
            if self.lot_sqft_max:
                message['lot_sqft_max'] = self.lot_sqft_max
            if self.year_built_min:
                message['year_built_min'] = self.year_built_min
            if self.year_built_max:
                message['year_built_max'] = self.year_built_max

            # Sorting
            if self.sort_by:
                message['sort_by'] = self.sort_by
            if self.sort_direction:
                message['sort_direction'] = self.sort_direction

            # Flags
            if self.mls_only:
                message['mls_only'] = self.mls_only
            if self.foreclosure:
                message['foreclosure'] = self.foreclosure
            if self.extra_property_data:
                message['extra_property_data'] = self.extra_property_data
            if self.exclude_pending:
                message['exclude_pending'] = self.exclude_pending

            # Other
            if self.proxy:
                message['proxy'] = self.proxy
            if self.limit:
                message['limit'] = self.limit

            # Connect to RabbitMQ
            credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_pass)

            parameters = pika.ConnectionParameters(
                host=rabbitmq_host,
                port=rabbitmq_port,
                credentials=credentials
            )

            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()

            # Declare exchange
            channel.exchange_declare(
                exchange=rabbitmq_exchange,
                exchange_type='topic',
                durable=True
            )

            # Publish message
            channel.basic_publish(
                exchange=rabbitmq_exchange,
                routing_key=rabbitmq_routing_key,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                    content_type='application/json'
                )
            )

            _logger.info(f"Published message to RabbitMQ: {message}")

            # Close connection
            connection.close()

            # Show success message to user
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': f'Property search request sent for {self.name}',
                    'sticky': False,
                    'type': 'success',
                }
            }

        except Exception as e:
            _logger.error(f"Error publishing to RabbitMQ: {str(e)}")
            raise UserError(f"Failed to send search request: {str(e)}")


class RealEstateSavedSearchPropertyType(models.Model):
    _name = 'real_estate.saved_search.property_type'
    _description = 'Property Types for Saved Searches'

    name = fields.Char(string='Display Name', required=True)
    code = fields.Char(string='Code', required=True, help='Technical code used in API requests')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Property type code must be unique!')
    ]
