/**
 * VMMC ERP — Reusable Pagination Engine  (vmmc-pagination.js)
 *
 * Usage:
 *   const pg = new VMMCPagination({
 *       containerId: 'myPaginationContainer',   // id of the footer wrapper div
 *       defaultPageSize: 25,                     // optional (default: 25)
 *       storageKey: 'vmmc_pg_myTable',           // optional localStorage key
 *       onPageChange: (page, pageSize) => {}     // callback when page/size changes
 *   });
 *
 *   // After data loads call:
 *   pg.setTotal(totalRecords);
 *   pg.render();
 *
 *   // To reset to page 1 (e.g. after a new search):
 *   pg.reset();
 */

class VMMCPagination {
    constructor(opts = {}) {
        this.containerId   = opts.containerId;
        this.defaultPageSize = parseInt(opts.defaultPageSize) || 25;
        this.storageKey    = opts.storageKey || null;
        this.onPageChange  = opts.onPageChange || null;

        // Restore from session or default
        this.pageSize = this._loadPageSize();
        this.currentPage = 1;
        this.totalRecords = 0;

        this._container = null;
    }

    // ── Public API ──────────────────────────────────────────────────────────────

    setTotal(n) {
        this.totalRecords = Math.max(0, parseInt(n) || 0);
    }

    reset() {
        this.currentPage = 1;
        this.render();
    }

    get totalPages() {
        return Math.max(1, Math.ceil(this.totalRecords / this.pageSize));
    }

    get startRecord() {
        if (this.totalRecords === 0) return 0;
        return (this.currentPage - 1) * this.pageSize + 1;
    }

    get endRecord() {
        return Math.min(this.currentPage * this.pageSize, this.totalRecords);
    }

    render() {
        if (!this._container) {
            this._container = document.getElementById(this.containerId);
        }
        if (!this._container) return;

        const totalPages = this.totalPages;

        // Build info text
        const infoText = this.totalRecords === 0
            ? 'Showing 0 to 0 of 0 entries'
            : `Showing ${this.startRecord} to ${this.endRecord} of ${this.totalRecords} entries`;

        // Build rows-per-page options
        const options = [10, 25, 50, 100];
        const selectOptions = options.map(o =>
            `<option value="${o}"${this.pageSize === o ? ' selected' : ''}>${o}</option>`
        ).join('');

        // Build page buttons (compact)
        const pageButtons = this._buildPageButtons(totalPages);

        this._container.innerHTML = `
            <div class="vmmc-pg-footer">
                <div class="vmmc-pg-info" id="${this.containerId}_info">${infoText}</div>
                <div class="vmmc-pg-controls">
                    <label class="vmmc-pg-label">Rows per page:
                        <select class="vmmc-pg-select" id="${this.containerId}_size">${selectOptions}</select>
                    </label>
                    <div class="vmmc-pg-buttons" id="${this.containerId}_btns">
                        ${pageButtons}
                    </div>
                </div>
            </div>
        `;

        // Bind page-size change
        const sel = document.getElementById(`${this.containerId}_size`);
        if (sel) {
            sel.addEventListener('change', (e) => {
                this.pageSize = parseInt(e.target.value);
                this._savePageSize(this.pageSize);
                this.currentPage = 1;
                this.render();
                if (this.onPageChange) this.onPageChange(this.currentPage, this.pageSize);
            });
        }

        // Bind page buttons
        const btnsEl = document.getElementById(`${this.containerId}_btns`);
        if (btnsEl) {
            btnsEl.querySelectorAll('[data-pg]').forEach(btn => {
                btn.addEventListener('click', () => {
                    const pg = parseInt(btn.getAttribute('data-pg'));
                    if (!isNaN(pg) && pg >= 1 && pg <= totalPages && pg !== this.currentPage) {
                        this.currentPage = pg;
                        this.render();
                        if (this.onPageChange) this.onPageChange(this.currentPage, this.pageSize);
                    }
                });
            });
        }
    }

    // ── Private helpers ─────────────────────────────────────────────────────────

    _buildPageButtons(totalPages) {
        const cur = this.currentPage;
        const isFirst = cur === 1;
        const isLast  = cur === totalPages;

        const btnStyle = (disabled, active) => {
            let style = 'font-size:0.8rem; padding:0.25rem 0.55rem; border-radius:5px; border:1px solid; cursor:pointer; line-height:1.4; font-family:inherit; transition:background 0.15s, color 0.15s;';
            if (disabled) {
                style += ' background:#f1f5f9; color:#94a3b8; border-color:#e2e8f0; cursor:not-allowed; opacity:0.6;';
            } else if (active) {
                style += ' background:var(--accent-blue,#2563eb); color:#fff; border-color:var(--accent-blue,#2563eb); font-weight:700;';
            } else {
                style += ' background:#fff; color:#475569; border-color:#e2e8f0;';
            }
            return style;
        };

        let html = '';

        // First <<
        html += `<button data-pg="1" style="${btnStyle(isFirst)}" ${isFirst ? 'disabled' : ''} title="First page">&laquo;</button>`;
        // Prev <
        html += `<button data-pg="${cur - 1}" style="${btnStyle(isFirst)}" ${isFirst ? 'disabled' : ''} title="Previous page">&lsaquo;</button>`;

        // Page numbers (compact: show up to 5 around current)
        const pages = this._pageRange(cur, totalPages);
        let prevPage = 0;
        for (const p of pages) {
            if (p === '...') {
                html += `<span style="padding:0.25rem 0.4rem; color:#94a3b8; font-size:0.8rem;">…</span>`;
            } else {
                html += `<button data-pg="${p}" style="${btnStyle(false, p === cur)}">${p}</button>`;
            }
            prevPage = p;
        }

        // Next >
        html += `<button data-pg="${cur + 1}" style="${btnStyle(isLast)}" ${isLast ? 'disabled' : ''} title="Next page">&rsaquo;</button>`;
        // Last >>
        html += `<button data-pg="${totalPages}" style="${btnStyle(isLast)}" ${isLast ? 'disabled' : ''} title="Last page">&raquo;</button>`;

        return html;
    }

    _pageRange(cur, total) {
        if (total <= 7) {
            return Array.from({length: total}, (_, i) => i + 1);
        }
        const pages = [];
        // Always show 1, last, and up to 2 around current
        const around = new Set([1, 2, cur - 1, cur, cur + 1, total - 1, total].filter(p => p >= 1 && p <= total));
        const sorted = [...around].sort((a, b) => a - b);

        let prev = 0;
        for (const p of sorted) {
            if (prev && p - prev > 1) pages.push('...');
            pages.push(p);
            prev = p;
        }
        return pages;
    }

    _loadPageSize() {
        if (this.storageKey) {
            const saved = sessionStorage.getItem(this.storageKey);
            if (saved && [10, 25, 50, 100].includes(parseInt(saved))) {
                return parseInt(saved);
            }
        }
        return this.defaultPageSize;
    }

    _savePageSize(size) {
        if (this.storageKey) {
            sessionStorage.setItem(this.storageKey, size);
        }
    }

    /**
     * Helper: given all fetched rows (array), returns the slice for the current page.
     * Use when all data is already in memory (JS-side pagination).
     */
    slice(allRows) {
        return allRows.slice(this.startRecord - 1, this.endRecord);
    }
}

/**
 * Inject global CSS for the pagination footer (once per page).
 */
(function injectPaginationStyles() {
    if (document.getElementById('vmmc-pg-style')) return;
    const style = document.createElement('style');
    style.id = 'vmmc-pg-style';
    style.textContent = `
        .vmmc-pg-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.75rem;
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid #e2e8f0;
            font-size: 0.82rem;
            color: #475569;
        }
        .vmmc-pg-info {
            font-weight: 500;
            color: #64748b;
        }
        .vmmc-pg-controls {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            flex-wrap: wrap;
        }
        .vmmc-pg-label {
            display: flex;
            align-items: center;
            gap: 0.4rem;
            color: #475569;
            font-weight: 500;
            white-space: nowrap;
        }
        .vmmc-pg-select {
            padding: 0.22rem 0.45rem;
            border: 1px solid #e2e8f0;
            border-radius: 5px;
            font-size: 0.8rem;
            background: #fff;
            color: #334155;
            cursor: pointer;
            height: auto;
            width: auto;
            font-family: inherit;
        }
        .vmmc-pg-select:focus {
            outline: 2px solid var(--accent-blue, #2563eb);
            outline-offset: 1px;
        }
        .vmmc-pg-buttons {
            display: flex;
            gap: 0.2rem;
            align-items: center;
            flex-wrap: wrap;
        }
        @media (max-width: 600px) {
            .vmmc-pg-footer {
                flex-direction: column;
                align-items: flex-start;
            }
        }
    `;
    document.head.appendChild(style);
})();
