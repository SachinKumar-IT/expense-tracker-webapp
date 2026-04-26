document.addEventListener('DOMContentLoaded', () => {
    // Theme Toggle Logic
    const themeToggleBtn = document.getElementById('themeToggle');
    const htmlElement = document.documentElement;
    
    // Check for saved theme preference or use system preference
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        htmlElement.setAttribute('data-bs-theme', savedTheme);
        updateIcon(savedTheme);
    } else {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const defaultTheme = prefersDark ? 'dark' : 'light';
        htmlElement.setAttribute('data-bs-theme', defaultTheme);
        updateIcon(defaultTheme);
    }

    // Toggle theme on button click
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            const currentTheme = htmlElement.getAttribute('data-bs-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            htmlElement.setAttribute('data-bs-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateIcon(newTheme);
            
            // Optionally update Chart.js colors if it's on the page
            if (window.Chart) {
                Chart.defaults.color = newTheme === 'dark' ? '#f8fafc' : '#1e293b';
                // Trigger resize to redraw charts
                window.dispatchEvent(new Event('resize'));
            }
        });
    }

    function updateIcon(theme) {
        if (!themeToggleBtn) return;
        const themeIcon = themeToggleBtn.querySelector('i');
        if (!themeIcon) return;
        
        if (theme === 'dark') {
            themeIcon.className = 'fa-solid fa-sun text-warning';
        } else {
            themeIcon.className = 'fa-solid fa-moon text-dark';
        }
    }
});
