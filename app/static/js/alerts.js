/* AppAlerts — single source of truth for user-facing alerts.
 *
 * Phase 4 (lean) — items 1, 2, 3, 4, 5, 6 of the checklist:
 *   - Unified severity-driven policy (no hardcoded 5/8/10s timeouts).
 *   - Important results stay visible until the user closes them.
 *   - Auto-close reserved for minor hints (one constant: MINOR_DISMISS_MS).
 *   - Avoids double/contradictory messages via dedup within DEDUP_WINDOW_MS.
 *   - Exposes escapeHtml() to keep templates safe.
 *
 * Severity contract:
 *   - `category: 'error'` and `category: 'destructive-success'` are sticky.
 *   - All other categories auto-dismiss after MINOR_DISMISS_MS.
 *   - `options.sticky` overrides the default per call.
 *
 * Server-rendered flash messages:
 *   - Templates set `data-sticky="true"` on the alert div for sticky ones.
 *   - This module scans the document on DOMContentLoaded and applies the
 *     same sticky/auto-dismiss behavior to those server-rendered alerts,
 *     so the user-visible behavior is consistent.
 */
(function (global) {
    'use strict';

    var MINOR_DISMISS_MS = 4000;
    var DEDUP_WINDOW_MS = 2000;

    var lastKey = null;
    var lastTime = 0;

    function escapeHtml(value) {
        var div = document.createElement('div');
        div.textContent = value == null ? '' : String(value);
        return div.innerHTML;
    }

    function defaultSticky(type, category) {
        if (category === 'error' || category === 'destructive-success') {
            return true;
        }
        if (type === 'danger' || type === 'warning') {
            return true;
        }
        return false;
    }

    function getContainer() {
        var existing = document.getElementById('app-alerts-container');
        if (existing) return existing;
        var container = document.createElement('div');
        container.id = 'app-alerts-container';
        container.className = 'app-alerts-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '1080';
        document.body.appendChild(container);
        return container;
    }

    function show(type, message, options) {
        options = options || {};
        var category = options.category || (type === 'danger' ? 'error' : 'info');
        var sticky = options.sticky !== undefined
            ? options.sticky
            : defaultSticky(type, category);
        var timeoutMs = options.timeoutMs || MINOR_DISMISS_MS;

        var key = String(type) + '|' + String(message);
        var now = Date.now();
        if (lastKey === key && (now - lastTime) < DEDUP_WINDOW_MS) {
            return null;
        }
        lastKey = key;
        lastTime = now;

        var container = getContainer();
        var alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-' + type + ' alert-dismissible fade show';
        if (sticky) alertDiv.classList.add('alert-permanent');
        alertDiv.setAttribute('role', 'alert');
        alertDiv.innerHTML = escapeHtml(message) +
            '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Cerrar"></button>';
        container.appendChild(alertDiv);

        if (!sticky) {
            setTimeout(function () {
                if (alertDiv.parentNode) alertDiv.remove();
            }, timeoutMs);
        }
        return alertDiv;
    }

    function classifyServerAlert(alertDiv) {
        /* Convert server-rendered flash messages to the same sticky behavior
         * based on their `data-sticky` attribute. Falls back to the
         * severity inferred from the alert-* class. */
        var stickyAttr = alertDiv.getAttribute('data-sticky');
        if (stickyAttr === 'true') return true;
        if (stickyAttr === 'false') return false;
        var className = alertDiv.className || '';
        if (className.indexOf('alert-danger') !== -1) return true;
        if (className.indexOf('alert-warning') !== -1) return true;
        return false;
    }

    function adoptServerAlerts() {
        /* On load, scan already-rendered alerts and apply sticky/dismiss. */
        var alerts = document.querySelectorAll('.alert.alert-dismissible');
        for (var i = 0; i < alerts.length; i++) {
            var alertDiv = alerts[i];
            if (classifyServerAlert(alertDiv)) {
                alertDiv.classList.add('alert-permanent');
            } else {
                (function (element) {
                    setTimeout(function () {
                        if (element.parentNode) element.remove();
                    }, MINOR_DISMISS_MS);
                })(alertDiv);
            }
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', adoptServerAlerts);
    } else {
        adoptServerAlerts();
    }

    global.AppAlerts = {
        show: show,
        escapeHtml: escapeHtml,
        MINOR_DISMISS_MS: MINOR_DISMISS_MS,
        DEDUP_WINDOW_MS: DEDUP_WINDOW_MS,
    };
})(window);
