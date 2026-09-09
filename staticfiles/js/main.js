document.addEventListener('DOMContentLoaded', () => {
    // Ensure window always opens scrolled to the top
    if ('scrollRestoration' in history) {
        history.scrollRestoration = 'manual';
    }
    window.scrollTo(0, 0);

    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('mainSidebar');
    const backdrop = document.getElementById('mobileSidebarBackdrop');

    // -------------------------------------------------------
    // DESKTOP COLLAPSE: uses 'sidebar-collapsed' class on sidebar
    // MOBILE DRAWER:    uses '-translate-x-full' class on sidebar
    // -------------------------------------------------------

    // Restore saved desktop collapse state
    const savedCollapsed = localStorage.getItem('vmmc_sidebar_collapsed') === 'true';
    if (savedCollapsed && sidebar && window.innerWidth >= 1024) {
        sidebar.classList.add('sidebar-collapsed');
        if (sidebarToggle) sidebarToggle.setAttribute('aria-expanded', 'false');
    } else if (!savedCollapsed && sidebarToggle) {
        sidebarToggle.setAttribute('aria-expanded', 'true');
    }

    // Toggle handler
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', () => {
            if (window.innerWidth < 1024) {
                // ---- MOBILE / TABLET: drawer open/close ----
                const isHidden = sidebar.classList.contains('-translate-x-full');
                sidebar.classList.toggle('-translate-x-full');
                if (backdrop) backdrop.classList.toggle('hidden', !isHidden);
                sidebarToggle.setAttribute('aria-expanded', isHidden ? 'true' : 'false');
                document.body.classList.toggle('sidebar-overlay-open', isHidden);
            } else {
                // ---- DESKTOP: collapse/expand ----
                const isCollapsed = sidebar.classList.toggle('sidebar-collapsed');
                localStorage.setItem('vmmc_sidebar_collapsed', isCollapsed);
                sidebarToggle.setAttribute('aria-expanded', isCollapsed ? 'false' : 'true');
            }
        });
    }

    // Close mobile drawer when backdrop is clicked
    if (backdrop) {
        backdrop.addEventListener('click', () => {
            sidebar.classList.add('-translate-x-full');
            backdrop.classList.add('hidden');
            document.body.classList.remove('sidebar-overlay-open');
            if (sidebarToggle) sidebarToggle.setAttribute('aria-expanded', 'false');
        });
    }

    // Close mobile drawer on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && window.innerWidth < 1024) {
            if (sidebar && !sidebar.classList.contains('-translate-x-full')) {
                sidebar.classList.add('-translate-x-full');
                if (backdrop) backdrop.classList.add('hidden');
                document.body.classList.remove('sidebar-overlay-open');
                if (sidebarToggle) {
                    sidebarToggle.setAttribute('aria-expanded', 'false');
                    sidebarToggle.focus();
                }
            }
        }
    });

    // On resize from mobile to desktop: reset mobile overlay state cleanly
    window.addEventListener('resize', () => {
        if (window.innerWidth >= 1024) {
            document.body.classList.remove('sidebar-overlay-open');
            if (backdrop) backdrop.classList.add('hidden');
            // Remove mobile translate class so sidebar is visible on desktop
            if (sidebar) sidebar.classList.remove('-translate-x-full');
        } else {
            // On resize to mobile, remove desktop collapse and ensure correct state
            if (sidebar) sidebar.classList.remove('sidebar-collapsed');
            // Ensure sidebar is hidden on mobile (drawer closed by default)
            if (sidebar && !document.body.classList.contains('sidebar-overlay-open')) {
                sidebar.classList.add('-translate-x-full');
            }
        }
    });

    // Accordion Sub-Menu Toggle
    const submenuToggles = document.querySelectorAll('.submenu-toggle');
    submenuToggles.forEach(toggle => {
        toggle.addEventListener('click', (e) => {
            e.preventDefault();
            const parentLi = toggle.closest('.has-submenu');
            if (parentLi) {
                parentLi.classList.toggle('open');
            }
        });
    });

    // Floating Scroll to Top button behavior
    const scrollToTopBtn = document.getElementById('scrollToTopBtn');
    if (scrollToTopBtn) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 150) {
                scrollToTopBtn.classList.add('visible');
            } else {
                scrollToTopBtn.classList.remove('visible');
            }
        });

        scrollToTopBtn.addEventListener('click', () => {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }
});

function togglePasswordVisibility(inputId, btn) {
    const input = document.getElementById(inputId);
    const icon = btn.querySelector('i');
    if (input && icon) {
        if (input.type === 'password') {
            input.type = 'text';
            icon.className = 'bi bi-eye-slash-fill';
        } else {
            input.type = 'password';
            icon.className = 'bi bi-eye-fill';
        }
    }
}
