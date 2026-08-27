class VMMCSearchSelect {
    constructor(containerSelector, options) {
        this.container = typeof containerSelector === 'string' ? document.querySelector(containerSelector) : containerSelector;
        if (!this.container) return;

        this.options = Object.assign({
            url: '',
            placeholder: 'Search...',
            minChars: 0,
            debounceTime: 250,
            searchParam: 'q',
            extraParams: () => ({}),
            processResults: (data) => data.results || data,
            renderMain: (item) => item.name || item.text || item.title || '',
            renderSub: (item) => item.code || item.id || '',
            onSelect: (item) => {},
            onClear: () => {},
            emptyText: 'No results found',
            errorText: 'Unable to load results. Please try again.',
            loadingText: 'Searching...'
        }, options);

        this.debounceTimer = null;
        this.results = [];
        this.highlightIndex = -1;
        this.selectedItem = null;

        this.initDOM();
        this.attachEvents();
    }

    initDOM() {
        this.container.classList.add('vmmc-search-select');
        this.container.innerHTML = `
            <div class="vss-input-wrapper">
                <i class="bi bi-search vss-icon"></i>
                <input type="text" class="vss-input" placeholder="${this.options.placeholder}" autocomplete="off">
                <div class="vss-spinner" style="display: none;"><i class="bi bi-arrow-repeat spin-icon"></i></div>
                <button type="button" class="vss-clear" style="display: none;"><i class="bi bi-x"></i></button>
            </div>
            <div class="vss-dropdown">
                <div class="vss-message vss-loading" style="display: none;">${this.options.loadingText}</div>
                <div class="vss-message vss-empty" style="display: none;">${this.options.emptyText}</div>
                <ul class="vss-list"></ul>
            </div>
        `;

        this.wrapper = this.container.querySelector('.vss-input-wrapper');
        this.input = this.container.querySelector('.vss-input');
        this.spinner = this.container.querySelector('.vss-spinner');
        this.clearBtn = this.container.querySelector('.vss-clear');
        this.dropdown = this.container.querySelector('.vss-dropdown');
        this.list = this.container.querySelector('.vss-list');
        this.loadingMsg = this.container.querySelector('.vss-loading');
        this.emptyMsg = this.container.querySelector('.vss-empty');
    }

    attachEvents() {
        this.input.addEventListener('focus', () => {
            this.wrapper.classList.add('active');
            if (this.input.value.trim().length >= this.options.minChars) {
                this.dropdown.classList.add('show');
                if (this.results.length === 0) this.fetchData(this.input.value);
            }
        });

        document.addEventListener('click', (e) => {
            if (!this.container.contains(e.target)) {
                this.closeDropdown();
            }
        });

        this.input.addEventListener('input', (e) => {
            const val = e.target.value;
            this.clearBtn.style.display = val.length > 0 ? 'block' : 'none';
            this.dropdown.classList.add('show');

            if (val.trim().length < this.options.minChars) {
                this.list.innerHTML = '';
                this.showEmpty();
                return;
            }

            clearTimeout(this.debounceTimer);
            this.showLoading();
            this.debounceTimer = setTimeout(() => this.fetchData(val), this.options.debounceTime);
        });

        this.clearBtn.addEventListener('click', () => {
            this.clear();
            this.input.focus();
        });

        this.input.addEventListener('keydown', (e) => this.handleKeydown(e));
    }

    async fetchData(query) {
        try {
            let url = new URL(this.options.url, window.location.origin);
            url.searchParams.set(this.options.searchParam, query.trim());
            
            const extra = typeof this.options.extraParams === 'function' ? this.options.extraParams() : this.options.extraParams;
            for (const key in extra) {
                url.searchParams.set(key, extra[key]);
            }

            const res = await fetch(url);
            if (!res.ok) throw new Error('API Error');
            const data = await res.json();
            
            this.results = this.options.processResults(data);
            this.renderList();
        } catch (err) {
            console.error('VMMCSelect fetch error:', err);
            this.list.innerHTML = '';
            this.hideAllMessages();
            this.emptyMsg.textContent = this.options.errorText;
            this.emptyMsg.style.display = 'block';
        }
    }

    renderList() {
        this.hideAllMessages();
        this.list.innerHTML = '';
        this.highlightIndex = -1;

        if (!this.results || this.results.length === 0) {
            this.emptyMsg.textContent = this.options.emptyText;
            this.showEmpty();
            return;
        }

        this.results.forEach((item, index) => {
            const li = document.createElement('li');
            li.className = 'vss-item';
            
            const main = this.options.renderMain(item);
            const sub = this.options.renderSub(item);
            
            li.innerHTML = `<div class="vss-item-main">${main}</div>`;
            if (sub) {
                li.innerHTML += `<div class="vss-item-sub">${sub}</div>`;
            }

            li.addEventListener('mouseenter', () => this.setHighlight(index));
            li.addEventListener('click', () => this.selectItem(item));
            this.list.appendChild(li);
        });
    }

    selectItem(item) {
        this.selectedItem = item;
        const mainText = this.options.renderMain(item);
        this.input.value = mainText;
        this.clearBtn.style.display = 'block';
        this.closeDropdown();
        this.options.onSelect(item);
    }

    clear() {
        this.input.value = '';
        this.clearBtn.style.display = 'none';
        this.selectedItem = null;
        this.results = [];
        this.list.innerHTML = '';
        this.options.onClear();
        this.fetchData('');
    }

    closeDropdown() {
        this.dropdown.classList.remove('show');
        this.wrapper.classList.remove('active');
    }

    showLoading() {
        this.list.innerHTML = '';
        this.hideAllMessages();
        this.loadingMsg.style.display = 'block';
        this.spinner.style.display = 'block';
    }

    showEmpty() {
        this.hideAllMessages();
        this.emptyMsg.style.display = 'block';
    }

    hideAllMessages() {
        this.loadingMsg.style.display = 'none';
        this.emptyMsg.style.display = 'none';
        this.spinner.style.display = 'none';
    }

    handleKeydown(e) {
        if (!this.dropdown.classList.contains('show')) {
            if (e.key === 'ArrowDown' || e.key === 'Enter') {
                this.dropdown.classList.add('show');
                if (this.results.length === 0) this.fetchData(this.input.value);
            }
            return;
        }

        const items = this.list.querySelectorAll('.vss-item');
        if (items.length === 0) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            this.setHighlight(this.highlightIndex + 1);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            this.setHighlight(this.highlightIndex - 1);
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (this.highlightIndex >= 0 && this.highlightIndex < this.results.length) {
                this.selectItem(this.results[this.highlightIndex]);
            }
        } else if (e.key === 'Escape') {
            this.closeDropdown();
        }
    }

    setHighlight(index) {
        const items = this.list.querySelectorAll('.vss-item');
        if (items.length === 0) return;

        items.forEach(el => el.classList.remove('highlighted'));
        
        if (index < 0) index = items.length - 1;
        if (index >= items.length) index = 0;
        
        this.highlightIndex = index;
        items[index].classList.add('highlighted');
        items[index].scrollIntoView({ block: 'nearest' });
    }
}
