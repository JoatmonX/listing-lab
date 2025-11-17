from odoo import models, fields


class RealEstateTag(models.Model):
    _name = 'real_estate.tag'
    _description = 'Real Estate Tags'

    name = fields.Char(
        string='Name',
        required=True
    )

    api_name = fields.Char(
        string='API Name'
    )

    color = fields.Integer(
        string='Color Index'
    )

    tag_type = fields.Selection(
        selection=[
            ('user', 'User Tag'),
            ('listing', 'Listing Tag'),
        ],
        string='Tag Type',
        default='user',
        help='Distinguish between user-created tags and tags coming from the listing source'
    )
