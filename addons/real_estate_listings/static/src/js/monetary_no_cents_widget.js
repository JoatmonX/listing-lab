/** @odoo-module **/

import {registry} from "@web/core/registry";
import {MonetaryField, monetaryField} from "@web/views/fields/monetary/monetary_field";
import {formatMonetary} from "@web/views/fields/formatters";
import {_t} from "@web/core/l10n/translation";

export class MonetaryNoCentsField extends MonetaryField {
    static template = MonetaryField.template;
    // Accept the same props as MonetaryField, plus an optional `options` prop
    // because <Field ... options="{...}"/> forwards this prop to the widget.
    static props = {
        ...MonetaryField.props,
        options: {type: Object, optional: true},
    };

    get formattedValue() {
        const value = this.props.record.data[this.props.name];

        if (value === false || value === undefined || value === null) {
            return "";
        }

        // Format monetary value without cents (no decimal places)
        return formatMonetary(value, {
            currencyId: this.currency?.id,
            currencyPosition: this.currency?.position,
            currencySymbol: this.currency?.symbol,
            digits: [69, 0], // Force 0 decimal places
        });
    }
}

export const monetaryNoCentsField = {
    ...monetaryField,
    component: MonetaryNoCentsField,
    displayName: _t("Monetary (No Cents)"),
};

registry.category("fields").add("monetary_no_cents", monetaryNoCentsField);