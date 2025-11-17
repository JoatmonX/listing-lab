import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class PropertyTaxHistory(models.Model):
    _name = 'real_estate.tax_history'
    _description = 'Property Tax History'
    _order = 'year desc'

    property_id = fields.Many2one(
        'real_estate.listing',
        string='Property',
        required=True,
        ondelete='cascade',
        help='Related property'
    )

    year = fields.Integer(
        string='Year',
        required=True,
        help='Tax year'
    )

    # Currency
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='property_id.currency_id',
        store=True,
        readonly=True,
        help='Currency for monetary values on this tax record'
    )

    tax = fields.Monetary(
        string='Tax Amount',
        currency_field='currency_id',
        help='Tax amount for the year'
    )

    assessment_total = fields.Monetary(
        string='Total Assessment',
        currency_field='currency_id',

        help='Total assessed value'
    )

    assessment_building = fields.Monetary(
        string='Building Assessment',
        currency_field='currency_id',

        help='Building assessed value'
    )

    assessment_land = fields.Monetary(
        string='Land Assessment',
        currency_field='currency_id',

        help='Land assessed value'
    )

    appraisal = fields.Monetary(
        string='Appraisal Value',
        currency_field='currency_id',

        help='Appraised value'
    )

    market = fields.Monetary(
        string='Market Value',
        currency_field='currency_id',

        help='Market value'
    )

    value = fields.Monetary(
        string='Value',
        currency_field='currency_id',

        help='Property value'
    )

    assessed_year = fields.Integer(
        string='Assessed Year',
        help='Year of assessment'
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
                    "[PropertyTaxHistory.%s] Sending bus notification | channel=%s type=%s payload=%s",
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
        # Normalize incoming data: RPC may pass field values as kwargs instead of a 'vals' dict
        normalized = vals if vals is not None else kwargs
        records = super().create(normalized)
        updated = []
        if isinstance(normalized, dict):
            updated = list(normalized.keys())
        elif isinstance(normalized, list) and normalized:
            updated = list(normalized[0].keys())
        self._notify_listing_bus(records.mapped("property_id.id"), updated, event="create")
        return records
