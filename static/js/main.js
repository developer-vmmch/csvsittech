document.addEventListener('DOMContentLoaded', () => {
    // Ensure window always opens scrolled to the top
    if ('scrollRestoration' in history) {
        history.scrollRestoration = 'manual';
    }
    window.scrollTo(0, 0);

    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('mainSidebar');
    const backdrop = document.getElementById('mobileSidebarBackdrop');

    // Load saved sidebar state for desktop
    const savedState = localStorage.getItem('vmmc_sidebar_collapsed');
    if (savedState === 'true' && sidebar && window.innerWidth >= 1024) {
        sidebar.classList.remove('lg:w-64');
        sidebar.classList.add('lg:w-20');
    }

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', () => {
            if (window.innerWidth < 1024) {
                // Mobile/tablet toggle — slide in/out as drawer
                const isHidden = sidebar.classList.contains('-translate-x-full');
                sidebar.classList.toggle('-translate-x-full');
                if (backdrop) backdrop.classList.toggle('hidden');
                // Body lock to prevent background scroll when overlay open
                document.body.classList.toggle('sidebar-overlay-open', isHidden);
            } else {
                // Desktop collapse toggle
                sidebar.classList.toggle('lg:w-64');
                sidebar.classList.toggle('lg:w-20');
                const isCollapsed = sidebar.classList.contains('lg:w-20');
                localStorage.setItem('vmmc_sidebar_collapsed', isCollapsed);
            }
        });
    }

    // Close sidebar on small screens when clicking backdrop
    if (backdrop) {
        backdrop.addEventListener('click', () => {
            sidebar.classList.add('-translate-x-full');
            backdrop.classList.add('hidden');
            document.body.classList.remove('sidebar-overlay-open');
        });
    }

    // On resize to desktop, clear body lock and reset overlay state
    window.addEventListener('resize', () => {
        if (window.innerWidth >= 1024) {
            document.body.classList.remove('sidebar-overlay-open');
            if (backdrop) backdrop.classList.add('hidden');
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
