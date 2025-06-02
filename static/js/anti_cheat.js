// Disable right-click context menu
document.addEventListener('contextmenu', event => event.preventDefault());

// Disable text selection
document.addEventListener('selectstart', event => event.preventDefault());

// Disable copy-paste and cut
document.addEventListener('copy', event => event.preventDefault());
document.addEventListener('paste', event => event.preventDefault());
document.addEventListener('cut', event => event.preventDefault());

// Disable keyboard shortcuts for developer tools
document.addEventListener('keydown', function(event) {
    // F12
    if (event.key === 'F12') {
        event.preventDefault();
    }
    // Ctrl+Shift+I
    if (event.ctrlKey && event.shiftKey && event.key === 'I') {
        event.preventDefault();
    }
    // Ctrl+Shift+J
    if (event.ctrlKey && event.shiftKey && event.key === 'J') {
        event.preventDefault();
    }
    // Ctrl+Shift+C
    if (event.ctrlKey && event.shiftKey && event.key === 'C') {
        event.preventDefault();
    }
    // Ctrl+U
    if (event.ctrlKey && event.key === 'U') {
        event.preventDefault();
    }
});
