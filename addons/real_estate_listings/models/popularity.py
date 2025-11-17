import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class RealEstatePopularity(models.Model):
    """
    Model to track popularity metrics for real estate listings
    """
    _name = 'real_estate.popularity'
    _description = 'Real Estate Popularity Metrics'

    property_id = fields.Many2one('real_estate.listing', string='Property', required=True, ondelete='cascade')
    last_n_days = fields.Integer(string='Period (days)', required=True)
    views_total = fields.Integer(string='Views', default=0)
    clicks_total = fields.Integer(string='Clicks', default=0)
    saves_total = fields.Integer(string='Saves', default=0)
    shares_total = fields.Integer(string='Shares', default=0)
    leads_total = fields.Integer(string='Leads', default=0)
    dwell_time_mean = fields.Float(string='Avg. Dwell Time', default=0.0)
    dwell_time_median = fields.Float(string='Median Dwell Time', default=0.0)

    _sql_constraints = [
        ('property_period_unique', 'unique(property_id, last_n_days)',
         'A popularity record for this period already exists!')
    ]

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
                    "[RealEstatePopularity.%s] Sending bus notification | channel=%s type=%s payload=%s",
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
        # Determine updated fields for payload
        updated = []
        if isinstance(normalized, dict):
            updated = list(normalized.keys())
        elif isinstance(normalized, list) and normalized:
            updated = list(normalized[0].keys())
        self._notify_listing_bus(records.mapped("property_id.id"), updated, event="create")
        return records
