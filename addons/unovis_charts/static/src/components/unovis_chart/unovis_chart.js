/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useRef, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";

/**
 * UnovisChart: a thin OWL wrapper for embedding any Unovis chart in portal pages.
 *
 * Props:
 * - initFnName?: string  // Name of a global function window[initFnName] that receives ({ el, Unovis, props }) and returns an instance with optional destroy()/update() methods.
 * - chartType?: string   // Optional. If provided, attempt to instantiate Unovis[chartType] with (el, props.options, props.data)
 * - options?: any        // Config/options passed to init function or constructor
 * - data?: any           // Data passed to init function or set on instance via setData/update
 * - width?: string       // Optional CSS width, e.g. '100%'
 * - height?: string      // Optional CSS height, e.g. '320px'
 */
export class UnovisChart extends Component {
    static template = "unovis_charts.UnovisChart";
    static props = {
        initFnName: { type: String, optional: true },
        chartType: { type: String, optional: true },
        options: { optional: true },
        data: { optional: true },
        width: { type: String, optional: true },
        height: { type: String, optional: true },
    };

    setup() {
        this.root = useRef("root");
        this._instance = null;
        this._unmounted = false;

        onMounted(async () => {
            await this._ensureUnovisLoaded();
            if (this._unmounted) return;
            this._initChart();
        });

        // When props.data changes (if the component is re-rendered), try to update
        useEffect(() => {
            this._updateChart();
        }, () => [this.props.data, this.props.options]);

        onWillUnmount(() => {
            this._unmounted = true;
            this._destroyChart();
        });
    }

    get _Unovis() {
        return window.Unovis || window.unovis || null;
    }

    async _ensureUnovisLoaded(maxWaitMs = 5000) {
        if (this._Unovis) return;
        // If a CDN loader was injected via assets.xml, wait a bit for it
        const start = Date.now();
        while (!this._Unovis && Date.now() - start < maxWaitMs) {
            await new Promise((r) => setTimeout(r, 100));
        }
        if (!this._Unovis) {
            console.warn("UnovisChart: Unovis global not found. Ensure @unovis/ts UMD is loaded on the page.");
        }
    }

    _initChart() {
        const el = this.root.el;
        const Unovis = this._Unovis;
        if (!el || !Unovis) return;

        try {
            if (this.props.initFnName && typeof window[this.props.initFnName] === "function") {
                this._instance = window[this.props.initFnName]({ el, Unovis, props: this.props });
                return;
            }
            if (this.props.chartType && Unovis[this.props.chartType]) {
                const Ctor = Unovis[this.props.chartType];
                // Try common constructor signatures
                try {
                    this._instance = new Ctor(el, this.props.options || {}, this.props.data);
                } catch (e) {
                    // Fallback to (el, options)
                    this._instance = new Ctor(el, this.props.options || {});
                    if (this.props.data && typeof this._instance.setData === "function") {
                        this._instance.setData(this.props.data);
                    }
                }
                return;
            }
            console.warn("UnovisChart: Neither initFnName nor valid chartType provided. Nothing to render.");
        } catch (err) {
            console.error("UnovisChart init error:", err);
        }
    }

    _updateChart() {
        const inst = this._instance;
        if (!inst) return;
        try {
            if (typeof inst.update === "function") {
                inst.update(this.props.options, this.props.data);
                return;
            }
            if (typeof inst.setData === "function" && this.props.data !== undefined) {
                inst.setData(this.props.data);
            }
            if (typeof inst.setConfig === "function" && this.props.options !== undefined) {
                inst.setConfig(this.props.options);
            }
        } catch (err) {
            console.debug("UnovisChart update failed; recreating instance.", err);
            this._destroyChart();
            this._initChart();
        }
    }

    _destroyChart() {
        const inst = this._instance;
        this._instance = null;
        if (!inst) return;
        try {
            if (typeof inst.destroy === "function") inst.destroy();
            else if (typeof inst.dispose === "function") inst.dispose();
        } catch (err) {
            console.debug("UnovisChart destroy error (ignored):", err);
        }
    }
}

// Make component available as a public component (usable in portal templates)
registry.category("public_components").add("unovis_charts.UnovisChart", UnovisChart);

export default UnovisChart;
