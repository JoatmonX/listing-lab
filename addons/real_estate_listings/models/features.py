import json
import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class PropertyFeature(models.Model):
    _name = 'real_estate.feature'
    _description = 'Property Features'
    _order = 'parent_category, category'

    property_id = fields.Many2one(
        'real_estate.listing',
        string='Property',
        required=True,
        ondelete='cascade',
        help='Related property listing'
    )

    parent_category = fields.Char(
        string='Parent Category',
        help='Parent category of the feature (e.g., Interior, Exterior, Community)'
    )

    category = fields.Char(
        string='Category',
        help='Category of the feature (e.g., Bedrooms, Bathrooms, Interior Features)'
    )

    text_items = fields.Text(
        string='Text Items',
        help='JSON-encoded list of text items for this feature'
    )

    # Computed field for display purposes
    display_text = fields.Html(
        string='Features',
        compute='_compute_display_text',
        store=False,
        help='Formatted display of feature text items'
    )

    @api.depends('text_items')
    def _compute_display_text(self):
        for record in self:
            if not record.text_items:
                record.display_text = ''
                continue

            try:
                items = json.loads(record.text_items)
                if not items:
                    record.display_text = ''
                    continue

                html = '<ul>'
                for item in items:
                    html += f'<li>{item}</li>'
                html += '</ul>'
                record.display_text = html
            except (json.JSONDecodeError, TypeError):
                record.display_text = f'<p>{record.text_items}</p>'

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
                    "[PropertyFeature.%s] Sending bus notification | channel=%s type=%s payload=%s",
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
        # Normalize incoming data: RPC may provide field values as kwargs instead of vals
        normalized = vals if vals is not None else kwargs
        records = super().create(normalized)
        updated = []
        if isinstance(normalized, dict):
            updated = list(normalized.keys())
        elif isinstance(normalized, list) and normalized:
            updated = list(normalized[0].keys())
        self._notify_listing_bus(records.mapped("property_id.id"), updated, event="create")
        return records
