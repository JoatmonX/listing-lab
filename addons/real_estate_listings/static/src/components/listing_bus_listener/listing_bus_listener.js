/** @odoo-module **/

import {Component, onWillStart, onWillUnmount, onWillUpdateProps, useState} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {registry} from "@web/core/registry";
import {standardFieldProps} from "@web/views/fields/standard_field_props";

const fieldRegistry = registry.category("fields");

export class ListingBusListener extends Component {
    static template = "real_estate_listings.ListingBusListener";
    static props = standardFieldProps;

    setup() {
        this.bus = useService("bus_service");
        this.state = useState({hasRemoteUpdate: false});

        // Simple debug logger
        this._log = (...args) => console.log("[ListingBusListener]", ...args);

        // Compute current channel name; return null when no valid id to avoid subscribing to `..._undefined`
        this.channel = (resId) => (resId ? `estate_property_${resId}` : null);
        this.currentChannel = null;
        this.busSubscriptionType = "estate_property_update";
        this._onBusMessage = this.onBusMessage.bind(this);

        // Helper to update the subscribed channel whenever resId changes (including after first save)
        this._updateChannelSubscription = (resId) => {
            const desired = this.channel(resId);
            if (this.currentChannel && this.currentChannel !== desired) {
                this._log("Resubscribe: deleteChannel", this.currentChannel);
                this.bus.deleteChannel(this.currentChannel);
                this.currentChannel = null;
            }
            if (desired && this.currentChannel !== desired) {
                this._log("Resubscribe: addChannel", desired);
                this.bus.addChannel(desired);
                this.currentChannel = desired;
            }
            if (!desired) {
                this._log("No channel to subscribe (missing resId)");
            }
        };

        // --- Debounce setup for reload requests ---
        // Coalesce rapid successive bus messages into a single reload
        this._reloadTimer = null;
        this._debounceDelayMs = 50; // reasonable default; avoids UI thrash yet feels responsive

        this._scheduleReload = async () => {
            // Reset existing timer if any
            if (this._reloadTimer) {
                clearTimeout(this._reloadTimer);
                this._reloadTimer = null;
            }
            this._reloadTimer = setTimeout(async () => {
                this._reloadTimer = null;
                // Before reloading, re-check dirty state to avoid losing unsaved edits that started after scheduling
                const root = this.props.record?.model?.root;
                let isDirtyAfterDelay;
                try {
                    const dirtyVal = typeof root?.isDirty === "function" ? root.isDirty() : root?.isDirty;
                    isDirtyAfterDelay = dirtyVal instanceof Promise ? await dirtyVal : !!dirtyVal;
                } catch (e) {
                    // Be conservative: skip auto reload if unsure
                    this._log("debounced reload: unable to confirm clean state; skipping", e);
                    isDirtyAfterDelay = true;
                }
                if (!isDirtyAfterDelay) {
                    this._log("debounced auto-reload starting");
                    this.reloadRecord();
                } else {
                    // If it became dirty in the meantime, show the refresh banner instead
                    this.state.hasRemoteUpdate = true;
                    this._log("debounced auto-reload cancelled due to dirty state; showing banner");
                }
            }, this._debounceDelayMs);
        };

        onWillStart(() => {
            const resId = this.props?.record?.resId;
            this._log("onWillStart", {resId});
            // Always subscribe to the notification type immediately
            this.bus.subscribe(this.busSubscriptionType, this._onBusMessage);
            // Add the specific channel if we already have an id (may be null for brand new)
            this._updateChannelSubscription(resId);

            // Start a lightweight poller to detect first-save id assignment (when props object doesn't reflow)
            // This avoids relying on useRecordObserver which is unavailable in this environment.
            this._idPoller = setInterval(() => {
                try {
                    const currentResId = this.props?.record?.resId;
                    if (currentResId && this.currentChannel !== this.channel(currentResId)) {
                        this._log("poller detected resId; updating channel", {currentResId});
                        this._updateChannelSubscription(currentResId);
                    }
                } catch (e) {
                    // Swallow errors; poller is best-effort
                }
            }, 1000);
        });

        onWillUnmount(() => {
            if (this.currentChannel) {
                this._log("Unsubscribing from channel", this.currentChannel);
                this.bus.deleteChannel(this.currentChannel);
                this.currentChannel = null;
            } else {
                this._log("onWillUnmount with no channel (missing resId)");
            }
            if (this.busSubscriptionType && this._onBusMessage) {
                this.bus.unsubscribe(this.busSubscriptionType, this._onBusMessage);
            }

            if (this._idPoller) {
                clearInterval(this._idPoller);
                this._idPoller = null;
            }

            if (this._reloadTimer) {
                clearTimeout(this._reloadTimer);
                this._reloadTimer = null;
            }
        });

        // If the active record changes (e.g., user navigates to another listing), resubscribe to the new channel
        onWillUpdateProps((nextProps) => {
            const prevResId = this.props?.record?.resId;
            const nextResId = nextProps?.record?.resId;
            this._log("onWillUpdateProps", {prevResId, nextResId});
            if (prevResId !== nextResId) {
                this._updateChannelSubscription(nextResId);
            }
        });
    }

    async onBusMessage(payload) {
        const resId = this.props.record?.resId;
        const chName = this.currentChannel;
        if (!resId || !chName) {
            this._log("bus message received but missing resId/channel", {resId, chName, payload});
            return;
        }

        // We already filtered by type via subscribe; ensure this message targets our record
        if (!payload || payload.id !== resId) {
            this._log("bus message ignored (different id)", {targetId: resId, got: payload?.id});
            return;
        }

        // Check if the current form has unsaved changes (support sync/async/boolean)
        const root = this.props.record?.model?.root;
        let isDirty;
        try {
            const dirtyVal = typeof root?.isDirty === "function" ? root.isDirty() : root?.isDirty;
            isDirty = dirtyVal instanceof Promise ? await dirtyVal : !!dirtyVal;
        } catch (e) {
            // If anything goes wrong, assume dirty to avoid unintended reloads
            this._log("error while checking dirty state; defaulting to dirty", e);
            isDirty = true;
        }
        this._log("matched bus message", {
            resId,
            isDirty,
            updated_fields: payload?.updated_fields,
        });

        if (!isDirty) {
            // Auto-reload if safe, but debounced to avoid thrashing on bursts
            this._log("queueing debounced auto-reload");
            this._scheduleReload();
        } else {
            // Show banner prompting refresh
            this.state.hasRemoteUpdate = true;
            this._log("showing refresh banner due to local dirty state");
        }
    }

    async reloadRecord() {
        const resId = this.props.record?.resId;
        if (!resId) {
            this._log("reloadRecord aborted: missing resId");
            return;
        }
        try {
            // In Odoo 19, Record.load() does not accept arguments; it reloads current record
            await this.props.record.model.root.load();
            this._log("reloadRecord completed");
        } catch (e) {
            this._log("reloadRecord failed", e);
        }
        this.state.hasRemoteUpdate = false;
    }

    onClickReloadFromServer() {
        this._log("manual refresh clicked");
        this.reloadRecord();
    }
}

fieldRegistry.add("listing_bus_listener", {
    component: ListingBusListener,
    supportedTypes: ["integer", "char", "many2one", "many2many", "one2many"],
});
