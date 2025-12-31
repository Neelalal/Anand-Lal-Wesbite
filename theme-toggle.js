function toggleDarkMode() {
    var body = document.body;
    var isChecked = document.getElementById('dark-mode-toggle').checked;
    if (isChecked) {
        body.classList.add("dark-mode");
    } else {
        body.classList.remove("dark-mode");
    }
}

// Set initial theme on page load
document.addEventListener('DOMContentLoaded', (event) => {
    var toggle = document.getElementById('dark-mode-toggle');
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        // If the OS is set to dark mode, we set the page to dark mode
        document.body.classList.add("dark-mode");
        toggle.checked = true;
    }
});