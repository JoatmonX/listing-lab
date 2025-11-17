/** @odoo-module **/

import {Component} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {standardFieldProps} from "@web/views/fields/standard_field_props";
import {Field} from "@web/views/fields/field";

const fieldRegistry = registry.category("fields");
const formatters = registry.category("formatters");

export class ListingSummary extends Component {
    static template = "real_estate_listings.ListingSummary";
    static props = standardFieldProps;
    static components = {Field};


    get record() {
        return this.props.record.data;
    }

    // --- Display helpers ---
    formatValue(fieldName, args) {
        const field = this.props.record.fields[fieldName];
        if (!field) {
            // Field not found on the record (e.g., bad caller). Fail gracefully.
            return "";
        }
        const formatter = formatters.get(field.type);
        return formatter(this.props.record.data[fieldName], {
            ...args,
            field,
        });
    }

    _stripCents(formatted) {
        if (!formatted) return "";
        const match = formatted.match(/^(.*?)([.,]\d{1,2})([^0-9]*)$/);

        if (match) {
            return `${match[1]}${match[3]}`.trim();
        }

        return formatted;
    }

    get price() {
        const value = this.record.price;

        if (!value) {
            return "";
        }

        return `$${Math.round(value).toLocaleString('en-US')}`;
    }

    get estimatedValue() {
        const value = this.record.estimated_value;

        if (!value) {
            return "-";
        }

        return `$${Math.round(value).toLocaleString('en-US')}`;
    }

    get pricePerSqft() {
        const value = this.record.price_per_sqft || this.record.unit_price;

        if (!value) {
            return "-";
        }

        return `$${Math.round(value).toLocaleString('en-US')}/sqft`;
    }

    get rentEstimate() {
        const value = this.record.estimated_monthly_rental;

        if (!value) {
            return "-";
        }
        return this.formatValue("estimated_monthly_rental", {}) + "/mo";
    }

    get bedsDisplay() {
        return this.record.bedrooms || 0;
    }

    get bathsDisplay() {
        const full = this.record.baths_full || 0;
        const half = this.record.baths_half || 0;
        return half ? `${full}.5` : `${full}`;
    }

    get sqftDisplay() {
        return this.record.sqft || "-";
    }

    get lotDisplay() {
        if (this.record.lot_acres) {
            return `${this.record.lot_acres.toFixed(2)} Acres Lot`;
        }
        if (this.record.lot_sqft) {
            return `${this.record.lot_sqft.toLocaleString()} Sqft Lot`;
        }
        return "-";
    }

    get propertyTypeLabel() {
        const map = {
            single_family: "Single Family Residence",
            multi_family: "Multi Family",
            condos: "Condo",
            condo_townhome: "Condo/Townhome",
            townhomes: "Townhome",
            duplex_triplex: "Duplex/Triplex",
            farm: "Farm",
            land: "Land",
            mobile: "Mobile Home",
        };
        return map[this.record.property_type] || "Home";
    }

    get marketStatusLabel() {
        const map = {
            active: "Active",
            pending: "Pending",
            contingent: "Contingent",
            sold: "Sold",
            off_market: "Off Market",
        };
        return map[this.record.market_status] || "";
    }

    get yearBuiltDisplay() {
        return this.record.year_built || "-";
    }

    get daysOnMarketDisplay() {
        const dom = this.record.days_on_market || this.record.days_on_mls;
        if (!dom) {
            return "";
        }
        return `${dom} days on market`;
    }
}

// ✅ Correct registry registration for Odoo 16
fieldRegistry.add("listing_summary", {
    component: ListingSummary,
    supportedTypes: ["monetary", "float", "integer", "char"],
});
