import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class RealEstateSchool(models.Model):
    _name = 'real_estate.school'
    _description = 'Nearby School'
    _order = 'name'

    name = fields.Char(string='Name', required=True, index=True)
    district = fields.Char(string='District')

    property_ids = fields.Many2many(
        'real_estate.listing',
        'real_estate_listing_school_rel',
        'school_id',
        'listing_id',
        string='Properties'
    )

    _sql_constraints = [
        ('school_name_uniq', 'unique(name)', 'A school with this name already exists.'),
    ]
