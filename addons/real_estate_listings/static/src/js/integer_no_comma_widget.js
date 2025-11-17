/** @odoo-module **/

import { registry } from "@web/core/registry";
import { IntegerField, integerField } from "@web/views/fields/integer/integer_field";
import { formatInteger } from "@web/views/fields/formatters";
import { _t } from "@web/core/l10n/translation";

export class IntegerNoCommaField extends IntegerField {
    static template = IntegerField.template;
    
    get formattedValue() {
        const value = this.props.record.data[this.props.name];
        if (value === false || value === undefined || value === null) {
            return "";
        }
        
        // Format integer value without comma separators
        return String(value);
    }
}

export const integerNoCommaField = {
    ...integerField,
    component: IntegerNoCommaField,
    displayName: _t("Integer (No Comma)"),
};

registry.category("fields").add("integer_no_comma", integerNoCommaField);