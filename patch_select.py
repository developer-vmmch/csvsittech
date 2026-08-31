import re

with open('static/js/vmmc-select.js', 'r') as f:
    content = f.read()

# 1. initDOM: create dropdown and append to document.body
old_initDOM = """    initDOM() {
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
    }"""

new_initDOM = """    initDOM() {
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
    }"""

content = content.replace(old_initDOM, new_initDOM)

# 2. Document click outside handler
old_click = """        document.addEventListener('click', (e) => {
            if (!this.container.contains(e.target)) {
                this.closeDropdown();
            }
        });"""

new_click = """        document.addEventListener('mousedown', (e) => {
            if (!this.container.contains(e.target) && !this.dropdown.contains(e.target)) {
                this.closeDropdown();
            }
        });"""
content = content.replace(old_click, new_click)

# Add scroll listener to attachEvents
old_attach = """        this.input.addEventListener('keydown', (e) => this.handleKeydown(e));
    }"""
new_attach = """        this.input.addEventListener('keydown', (e) => this.handleKeydown(e));
        
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
    }"""
content = content.replace(old_attach, new_attach)


# 3. openDropdown and updatePosition
old_open = """    openDropdown() {
        this.dropdown.classList.add('show');
        
        const rect = this.wrapper.getBoundingClientRect();
        const spaceBelow = window.innerHeight - rect.bottom;
        const spaceAbove = rect.top;
        const dropdownHeight = 260; // Max height we set in CSS

        if (spaceBelow < dropdownHeight && spaceAbove > spaceBelow) {
            this.dropdown.classList.add('dropup');
        } else {
            this.dropdown.classList.remove('dropup');
        }
    }"""

new_open = """    updatePosition() {
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
    }"""

content = content.replace(old_open, new_open)

# 4. mousedown on items
old_item = """            li.addEventListener('mouseenter', () => this.setHighlight(index));
            li.addEventListener('click', () => this.selectItem(item));
            this.list.appendChild(li);"""

new_item = """            li.addEventListener('mouseenter', () => this.setHighlight(index));
            li.addEventListener('mousedown', (e) => {
                // Prevent input blur and guarantee selection registers before outside clicks
                e.preventDefault();
                this.selectItem(item);
            });
            li.addEventListener('click', (e) => {
                e.preventDefault();
            });
            this.list.appendChild(li);"""

content = content.replace(old_item, new_item)

with open('static/js/vmmc-select.js', 'w') as f:
    f.write(content)

