document.addEventListener('DOMContentLoaded', () => {
    // Ensure window always opens scrolled to the top
    if ('scrollRestoration' in history) {
        history.scrollRestoration = 'manual';
    }
    window.scrollTo(0, 0);

    const sidebarToggle = document.getElementById('sidebarToggle');
    const body = document.body;

    // Load saved sidebar state
    const savedState = localStorage.getItem('vmmc_sidebar_collapsed');
    if (savedState === 'true') {
        body.classList.add('sidebar-collapsed');
    }

    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', () => {
            if (window.innerWidth <= 992) {
                body.classList.toggle('sidebar-open');
                body.classList.remove('sidebar-collapsed');
            } else {
                body.classList.toggle('sidebar-collapsed');
                body.classList.remove('sidebar-open');
                const isCollapsed = body.classList.contains('sidebar-collapsed');
                localStorage.setItem('vmmc_sidebar_collapsed', isCollapsed);
            }
        });
    }

    // Close sidebar on small screens when clicking outside
    document.addEventListener('click', (e) => {
        if (window.innerWidth <= 992 && body.classList.contains('sidebar-open')) {
            const sidebar = document.querySelector('.sidebar');
            if (sidebar && !sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
                body.classList.remove('sidebar-open');
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
