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
        `;

        this.dropdown = document.createElement('div');
        this.dropdown.className = 'vmmc-search-select-dropdown vss-dropdown';
        this.dropdown.innerHTML = `
            <div class="vss-message vss-loading" style="display: none;">${this.options.loadingText}</div>
            <div class="vss-message vss-empty" style="display: none;">${this.options.emptyText}</div>
            <ul class="vss-list"></ul>
        `;
        document.body.appendChild(this.dropdown);

        this.wrapper = this.container.querySelector('.vss-input-wrapper');
        this.input = this.container.querySelector('.vss-input');
        this.spinner = this.container.querySelector('.vss-spinner');
        this.clearBtn = this.container.querySelector('.vss-clear');
        this.list = this.dropdown.querySelector('.vss-list');
        this.loadingMsg = this.dropdown.querySelector('.vss-loading');
        this.emptyMsg = this.dropdown.querySelector('.vss-empty');
    }

    attachEvents() {
        this.input.addEventListener('focus', () => {
            this.wrapper.classList.add('active');
            if (this.input.value.trim().length >= this.options.minChars) {
                this.openDropdown();
                if (this.results.length === 0) this.fetchData(this.input.value);
            }
        });

        document.addEventListener('mousedown', (e) => {
            if (!this.container.contains(e.target) && !this.dropdown.contains(e.target)) {
                this.closeDropdown();
            }
        });

        this.input.addEventListener('input', (e) => {
            const val = e.target.value;
            this.clearBtn.style.display = val.length > 0 ? 'block' : 'none';
            this.openDropdown();

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
        
        window.addEventListener('scroll', () => {
            if (this.dropdown.classList.contains('show')) {
                this.updatePosition();
            }
        }, true);
        window.addEventListener('resize', () => {
            if (this.dropdown.classList.contains('show')) {
                this.updatePosition();
            }
        });
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
            li.addEventListener('mousedown', (e) => {
                // Prevent input blur and guarantee selection registers before outside clicks
                e.preventDefault();
                this.selectItem(item);
            });
            li.addEventListener('click', (e) => {
                e.preventDefault();
            });
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

    setValue(id, mainText, subText) {
        this.selectedItem = { id: id, text: mainText, code: subText };
        this.input.value = mainText;
        this.clearBtn.style.display = 'block';
    }

    closeDropdown() {
        this.dropdown.classList.remove('show');
        this.wrapper.classList.remove('active');
    }

    updatePosition() {
        if (!this.dropdown.classList.contains('show')) return;
        const rect = this.wrapper.getBoundingClientRect();
        const spaceBelow = window.innerHeight - rect.bottom;
        const spaceAbove = rect.top;
        const dropdownHeight = 260;
        
        this.dropdown.style.position = 'fixed';
        this.dropdown.style.left = rect.left + 'px';
        this.dropdown.style.width = rect.width + 'px';
        this.dropdown.style.zIndex = '999999';

        if (spaceBelow < dropdownHeight && spaceAbove > spaceBelow) {
            this.dropdown.classList.add('dropup');
            this.dropdown.style.top = 'auto';
            this.dropdown.style.bottom = (window.innerHeight - rect.top + 4) + 'px';
        } else {
            this.dropdown.classList.remove('dropup');
            this.dropdown.style.top = (rect.bottom + 4) + 'px';
            this.dropdown.style.bottom = 'auto';
        }
    }

    openDropdown() {
        this.dropdown.classList.add('show');
        this.updatePosition();
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
                this.openDropdown();
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

    setDisabled(disabled) {
        this.input.disabled = disabled;
        if (disabled) {
            this.container.classList.add('vss-disabled');
            this.wrapper.style.backgroundColor = '#f1f5f9';
            this.input.style.backgroundColor = '#f1f5f9';
            this.input.style.cursor = 'not-allowed';
            this.closeDropdown();
        } else {
            this.container.classList.remove('vss-disabled');
            this.wrapper.style.backgroundColor = '#fff';
            this.input.style.backgroundColor = '#fff';
            this.input.style.cursor = 'text';
        }
    }
}
