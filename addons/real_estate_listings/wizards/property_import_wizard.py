import json
import logging
import os

from odoo import models, fields, api
from odoo.exceptions import UserError
from openai import OpenAI

_logger = logging.getLogger(__name__)

class PropertyImportWizard(models.TransientModel):
    _name = 'property.import.wizard'
    _description = 'Property Import Wizard'

    natural_language_request = fields.Text(
        string='Natural Language Request',
        required=True,
        help='Describe the property or search criteria in natural language'
    )
    
    def action_process_request(self):
        """
        Process the natural language request using ChatGPT
        and create either a property or a saved search
        """
        self.ensure_one()
        
        if not self.natural_language_request:
            raise UserError("Please provide a natural language request.")
            
        # Get the API key from environment variable
        api_key = os.environ.get('OPENAI_API_KEY')
        
        if not api_key:
            raise UserError(
                'ChatGPT API key not configured. Please set the OPENAI_API_KEY environment variable.'
            )
            
        try:
            # Initialize OpenAI client
            client = OpenAI(api_key=api_key)
            
            # Prepare the prompt for ChatGPT
            prompt = f"""
            Based on the following natural language request, determine if the user wants to:
            1. Create a specific property listing, or
            2. Create a saved search for properties
            
            Then, extract the relevant information and format it as JSON.
            
            For a property listing, include:
            - address: The full address of the property
            - price: The listing price
            - beds: Number of bedrooms
            - baths: Number of bathrooms
            - sqft: Square footage
            - description: A brief description
            - property_type: Type of property (single_family, condo, etc.)
            
            For a saved search, include:
            - name: A name for the saved search
            - location: The location to search in
            - listing_type: Type of listing (for_sale, sold, pending)
            - beds_min: Minimum number of bedrooms
            - beds_max: Maximum number of bedrooms
            - baths_min: Minimum number of bathrooms
            - baths_max: Maximum number of bathrooms
            - price_min: Minimum price
            - price_max: Maximum price
            - sqft_min: Minimum square footage
            - sqft_max: Maximum square footage
            
            Also include a "type" field with value either "property" or "saved_search".
            
            Natural language request: {self.natural_language_request}
            """
            
            # Call ChatGPT API
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts structured data from natural language requests about real estate."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1000
            )
            
            # Extract the response content
            content = response.choices[0].message.content
            
            # Try to parse JSON from the response
            try:
                # Find JSON in the response (it might be surrounded by text)
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    data = json.loads(json_str)
                else:
                    raise ValueError("No JSON found in the response")
                    
                # Check if the type is specified
                if 'type' not in data:
                    raise ValueError("Type not specified in the response")
                    
                # Process based on the type
                if data['type'] == 'property':
                    return self._create_property(data)
                elif data['type'] == 'saved_search':
                    return self._create_saved_search(data)
                else:
                    raise ValueError(f"Unknown type: {data['type']}")
                    
            except json.JSONDecodeError as e:
                _logger.error(f"Failed to parse JSON from ChatGPT response: {e}")
                _logger.error(f"Response content: {content}")
                raise UserError(f"Failed to parse response from ChatGPT: {str(e)}")
                
        except Exception as e:
            _logger.error(f"Error processing request with ChatGPT: {str(e)}")
            raise UserError(f"Failed to process request: {str(e)}")
    
    def _create_property(self, data):
        """
        Create a property record from the parsed data
        """
        RealEstate = self.env['real_estate.listing']
        
        # Prepare values for creating the property
        vals = {
            'address': data.get('address', ''),
            'price': data.get('price', 0),
            'bedrooms': data.get('beds', 0),
            'baths_full': data.get('baths', 0),
            'sqft': data.get('sqft', 0),
            'note': data.get('description', ''),
            'property_type': data.get('property_type', 'single_family'),
        }
        
        # Create the property
        property_id = RealEstate.create(vals)
        
        # Trigger property scraping
        try:
            property_id.action_scrape_property()
        except Exception as e:
            _logger.warning(f"Failed to scrape property: {str(e)}")
        
        # Return action to open the created property
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'real_estate.listing',
            'res_id': property_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _create_saved_search(self, data):
        """
        Create a saved search record from the parsed data
        """
        SavedSearch = self.env['real_estate.saved_search']
        
        # Prepare values for creating the saved search
        vals = {
            'name': data.get('name', 'New Search'),
            'location': data.get('location', ''),
            'listing_type': data.get('listing_type', 'for_sale'),
            'beds_min': data.get('beds_min', 0),
            'beds_max': data.get('beds_max', 0),
            'baths_min': data.get('baths_min', 0),
            'baths_max': data.get('baths_max', 0),
            'price_min': data.get('price_min', 0),
            'price_max': data.get('price_max', 0),
            'sqft_min': data.get('sqft_min', 0),
            'sqft_max': data.get('sqft_max', 0),
        }
        
        # Create the saved search
        search_id = SavedSearch.create(vals)
        
        # Return action to open the created saved search
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'real_estate.saved_search',
            'res_id': search_id.id,
            'view_mode': 'form',
            'target': 'current',
        }