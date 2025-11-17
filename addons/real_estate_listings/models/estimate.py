import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class PropertyEstimate(models.Model):
    _name = 'real_estate.estimate'
    _description = 'Property Value Estimate'
    _order = 'date desc'

    property_id = fields.Many2one(
        'real_estate.listing',
        string='Property',
        required=True,
        ondelete='cascade',
        help='Related property'
    )

    date = fields.Date(
        string='Date',
        required=True,
        help='Date of the estimate'
    )

    # Currency
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='property_id.currency_id',
        store=True,
        readonly=True,
        help='Currency for monetary values on this estimate'
    )

    estimate = fields.Monetary(
        string='Estimate',
        currency_field='currency_id',

        help='Estimated property value'
    )

    estimate_high = fields.Monetary(
        string='High Estimate',
        currency_field='currency_id',

        help='High end of estimated property value range'
    )

    estimate_low = fields.Monetary(
        string='Low Estimate',
        currency_field='currency_id',

        help='Low end of estimated property value range'
    )

    is_best_home_value = fields.Boolean(
        string='Best Home Value',
        default=False,
        help='Indicates if this is considered the best home value estimate'
    )

    source_name = fields.Char(
        string='Source Name',
        help='Name of the estimate source (e.g., CoreLogic, Collateral Analytics)'
    )

    source_type = fields.Char(
        string='Source Type',
        help='Type of the estimate source'
    )

    # --- Live refresh notifications ---
    def _notify_listing_bus(self, listing_ids, updated_fields=None, event="write"):
        """Send a bus notification for the given listing IDs so other clients refresh.

        listing_ids: iterable of real_estate.listing ids
        updated_fields: list of field names changed
        event: 'create' | 'write'
        """
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
                    "[PropertyEstimate.%s] Sending bus notification | channel=%s type=%s payload=%s",
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
        # Notify related listing(s)
        self._notify_listing_bus(self.mapped("property_id.id"), list(vals.keys()), event="write")
        return res

    @api.model
    def create(self, vals=None, **kwargs):
        # RPC (json2) may pass field values as kwargs instead of a 'vals' dict
        normalized = vals if vals is not None else kwargs
        records = super().create(normalized)
        # Determine updated fields keys for payload (best effort)
        updated = []
        if isinstance(normalized, dict):
            updated = list(normalized.keys())
        elif isinstance(normalized, list) and normalized:
            updated = list(normalized[0].keys())
        self._notify_listing_bus(records.mapped("property_id.id"), updated, event="create")
        return records
