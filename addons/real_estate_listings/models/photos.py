import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class RealEstatePhoto(models.Model):
    _name = 'real_estate.photo'
    _description = 'Real Estate Property Photos'

    # Link to the property listing
    property_id = fields.Many2one(
        'real_estate.listing',
        string='Property',
        required=True,
        ondelete='cascade',
        help='Related property listing'
    )

    # Photo URL
    preview_href = fields.Char(
        string='Preview URL',
        required=True,
        help='URL to the property photo'
    )

    href = fields.Char(
        string='Full URL',
        help='Full URL to the property photo'
    )

    # Photo title (if available)
    title = fields.Char(
        string='Title',
        help='Title or description of the photo'
    )

    # Tags as a Many2many field to allow multiple tags per photo
    tag_ids = fields.Many2many(
        'real_estate.photo.tag',
        string='Tags',
        help='Tags describing the photo content (e.g., exterior, kitchen)'
    )

    # Sequence field for ordering photos
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Sequence order for displaying photos'
    )

    # Is primary photo
    is_primary = fields.Boolean(
        string='Primary Photo',
        default=False,
        help='Indicates if this is the primary photo for the property'
    )

    # --- Live refresh notifications ---
    def _notify_listing_bus(self, listing_ids, updated_fields=None, event="write"):
        try:
            bus = self.env["bus.bus"]
            for lid in set(listing_ids):
                if not lid:
                    continue
                channel = f"estate_property_{lid}"
                payload = {
                    "id": lid,
                    "model": "real_estate.listing",
                    "updated_fields": updated_fields or [],
                    "source_model": self._name,
                    "event": event,
                }
                _logger.info(
                    "[RealEstatePhoto.%s] Sending bus notification | channel=%s type=%s payload=%s",
                    event,
                    channel,
                    "estate_property_update",
                    payload,
                )
                bus._sendone(channel, "estate_property_update", payload)
        except Exception as e:
            _logger.warning("Failed to send bus notification for %s: %s", self._name, e)

    def write(self, vals):
        res = super().write(vals)
        self._notify_listing_bus(self.mapped("property_id.id"), list(vals.keys()), event="write")
        return res

    @api.model
    def create(self, vals=None, **kwargs):
        # Normalize incoming data: RPC may pass values as kwargs (json2)
        normalized = vals if vals is not None else kwargs
        records = super().create(normalized)
        updated = []
        if isinstance(normalized, dict):
            updated = list(normalized.keys())
        elif isinstance(normalized, list) and normalized:
            updated = list(normalized[0].keys())
        self._notify_listing_bus(records.mapped("property_id.id"), updated, event="create")
        return records

    def action_view_related_page(self):
        """Open the related property listing"""
        self.ensure_one()
        return {
            'name': f'Property - {self.property_id.address}',
            'type': 'ir.actions.act_window',
            'res_model': 'real_estate.listing',
            'res_id': self.property_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class RealEstatePhotoTag(models.Model):
    _name = 'real_estate.photo.tag'
    _description = 'Real Estate Photo Tags'

    name = fields.Char(
        string='Label',
        required=True,
        help='Tag label (e.g., exterior, kitchen, bathroom)'
    )

    color = fields.Integer(
        string='Color Index'
    )
