/**
 * Lab Master Lightweight UI Controller
 * Handles modal dialogs, backdrop clicks, escape dismissals,
 * and provides full backward compatibility for bootstrap.Modal callers.
 */

(function () {
    'use strict';

    function getModal(target) {
        if (!target) return null;
        if (typeof target === 'string') {
            return document.getElementById(target.replace('#', ''));
        }
        if (target instanceof HTMLElement) {
            return target.classList.contains('lab-modal') || target.classList.contains('modal')
                ? target
                : target.closest('.lab-modal, .modal');
        }
        return null;
    }

    window.openLabModal = function (target) {
        const modal = getModal(target);
        if (!modal) return;

        // Ensure both classes are supported
        modal.classList.add('show');
        modal.style.display = 'flex';
        modal.setAttribute('aria-hidden', 'false');
        document.body.classList.add('lab-modal-open');

        // Focus first visible input
        const firstInput = modal.querySelector('input:not([type="hidden"]), select, textarea');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 50);
        }
    };

    window.closeLabModal = function (target) {
        const modal = getModal(target);
        if (!modal) return;

        modal.classList.remove('show');
        modal.style.display = 'none';
        modal.setAttribute('aria-hidden', 'true');

        // Only remove body scroll lock if no other modals are open
        const anyOpen = document.querySelectorAll('.lab-modal.show, .modal.show');
        if (anyOpen.length === 0) {
            document.body.classList.remove('lab-modal-open');
        }
    };

    // Global Click Delegation for dismiss buttons and backdrop
    document.addEventListener('click', function (e) {
        const dismissBtn = e.target.closest('[data-lab-dismiss="modal"], [data-bs-dismiss="modal"], .lab-modal-close, .btn-close');
        if (dismissBtn) {
            const modal = dismissBtn.closest('.lab-modal, .modal');
            if (modal) {
                e.preventDefault();
                window.closeLabModal(modal);
            }
            return;
        }

        // Backdrop click dismiss
        if (e.target.classList.contains('lab-modal') || (e.target.classList.contains('modal') && e.target.classList.contains('show'))) {
            window.closeLabModal(e.target);
        }
    });

    // Escape Key Dismissal
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            const openModals = document.querySelectorAll('.lab-modal.show, .modal.show');
            if (openModals.length > 0) {
                const topModal = openModals[openModals.length - 1];
                window.closeLabModal(topModal);
            }
        }
    });

    // Bootstrap Modal Shim
    // Allows `new bootstrap.Modal(elem).show()` and `.hide()` to work without loading full bootstrap.js
    window.bootstrap = window.bootstrap || {};
    window.bootstrap.Modal = function (element) {
        this.element = typeof element === 'string' ? document.getElementById(element.replace('#', '')) : element;
        this.show = function () {
            window.openLabModal(this.element);
        };
        this.hide = function () {
            window.closeLabModal(this.element);
        };
    };
    window.bootstrap.Modal.getInstance = function (element) {
        const el = typeof element === 'string' ? document.getElementById(element.replace('#', '')) : element;
        return el ? new window.bootstrap.Modal(el) : null;
    };
    window.bootstrap.Modal.getOrCreateInstance = function (element) {
        return window.bootstrap.Modal.getInstance(element);
    };

})();
