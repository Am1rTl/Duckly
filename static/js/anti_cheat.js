'use strict';

function showDevToolsWarning() {
    // Attempt to stop further loading/scripting.
    try { window.stop(); } catch (e) { /* ignore */ }

    const warningHTML = `
        <div style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background-color: rgba(0,0,0,0.97); color: white; z-index: 2147483647; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; font-size: 24px; font-family: 'Poppins', sans-serif;">
            <div style="font-size: 60px; margin-bottom: 20px;">⚠️</div>
            <h1 style="font-size: 36px; margin-bottom: 15px; font-weight: 600;">Developer Tools Active</h1>
            <p style="font-size: 18px; line-height: 1.6; max-width: 600px;">Please close developer tools to access this page.</p>
            <p style="font-size: 14px; margin-top:30px; color: #ccc;">Further interaction is disabled.</p>
        </div>
    `;

    // Try to replace body. If body not ready, wait for it or replace entire document.
    if (document.body) {
        document.body.innerHTML = warningHTML;
        document.body.style.overflow = 'hidden'; // Prevent scrolling if anything was there
    } else {
        // This is a fallback. The debugger check aims to prevent reaching here with dev tools open.
        document.addEventListener('DOMContentLoaded', () => {
            if (document.body) {
                document.body.innerHTML = warningHTML;
                document.body.style.overflow = 'hidden';
            } else {
                // Absolute fallback if body never appears or script is in a weird state
                document.documentElement.innerHTML = `<html><head><title>Error</title></head><body>${warningHTML}</body></html>`;
            }
        });
    }
    // This is a critical part: make it extremely hard to remove the overlay.
    // Re-check and re-apply, in case the user tries to manipulate the DOM.
    setTimeout(() => {
        const overlay = document.querySelector('div[style*="z-index: 2147483647"]');
        if (!overlay) { // If removed, re-add
            if (document.body) document.body.innerHTML = warningHTML;
            else document.documentElement.innerHTML = `<html><head><title>Error</title></head><body>${warningHTML}</body></html>`;
        }
    }, 50); // Check very quickly
}

// --- IMMEDIATE DEV TOOLS CHECK ---
// This self-invoking function runs as soon as the script is parsed.
// Crucial for synchronous loading in <head>.
(function() {
    let devToolsDetectedInImmediateCheck = false;

    // Check 1: Debugger timing
    const startTime = new Date().getTime();
    debugger; // Execution will pause here IF dev tools are open
    const endTime = new Date().getTime();

    if ((endTime - startTime) > 100) { // Heuristic: 100ms+ delay suggests debugger was open
        devToolsDetectedInImmediateCheck = true;
        showDevToolsWarning();
        // Attempt to halt further script execution on the page.
        // This will stop this script, and hopefully prevent others if it's early enough.
        throw new Error("DevTools Detected (timing): Execution halted. Timestamp: " + new Date().toISOString());
    }

    // Check 2: Window dimension difference (less effective if dev tools are undocked)
    // Only run if not already detected by debugger
    if (!devToolsDetectedInImmediateCheck) {
        const threshold = 160;
        if (typeof window !== 'undefined' && (
            (window.outerWidth - window.innerWidth) > threshold ||
            (window.outerHeight - window.innerHeight) > threshold
        )) {
            devToolsDetectedInImmediateCheck = true;
            showDevToolsWarning();
            throw new Error("DevTools Detected (Window Size): Execution halted. Timestamp: " + new Date().toISOString());
        }
    }

    // If neither of the above immediate checks detected dev tools:
    if (!devToolsDetectedInImmediateCheck) {
        window.antiCheatInitialCheckPassed = true;
        // console.log("Anti-cheat initial checks passed."); // For debugging during development
    }
})();
// --- END OF IMMEDIATE CHECK ---


// Disable right-click context menu
document.addEventListener('contextmenu', event => {
    event.preventDefault();
    showDevToolsWarning(); // Also trigger warning if they try to bypass with right click
    return false;
});

// Disable text selection
document.addEventListener('selectstart', event => {
    event.preventDefault();
    return false;
});

// Disable copy-paste and cut
document.addEventListener('copy', event => {
    event.preventDefault();
    return false;
});
document.addEventListener('paste', event => {
    event.preventDefault();
    return false;
});
document.addEventListener('cut', event => {
    event.preventDefault();
    return false;
});

// Disable keyboard shortcuts for developer tools and other potential "cheats"
document.addEventListener('keydown', function(event) {
    let devToolsOpened = false;
    // F12
    if (event.key === 'F12' || event.keyCode === 123) {
        devToolsOpened = true;
    }
    // Ctrl+Shift+I / Cmd+Opt+I
    if ((event.ctrlKey || event.metaKey) && event.shiftKey && (event.key === 'I' || event.keyCode === 73)) {
        devToolsOpened = true;
    }
    // Ctrl+Shift+J / Cmd+Opt+J
    if ((event.ctrlKey || event.metaKey) && event.shiftKey && (event.key === 'J' || event.keyCode === 74)) {
        devToolsOpened = true;
    }
    // Ctrl+Shift+C / Cmd+Opt+C
    if ((event.ctrlKey || event.metaKey) && event.shiftKey && (event.key === 'C' || event.keyCode === 67)) {
        devToolsOpened = true;
    }
    // Ctrl+U / Cmd+U (View Source)
    if ((event.ctrlKey || event.metaKey) && (event.key === 'U' || event.keyCode === 85)) {
        devToolsOpened = true; // Treat view source as a dev tool attempt
    }

    if (devToolsOpened) {
        event.preventDefault();
        showDevToolsWarning();
        return false;
    }
});


// --- ONGOING CHECKS ---
// Function to check for developer tools (primarily window size)
function ongoingCheckDevTools() {
    const threshold = 160;
    if (typeof window !== 'undefined' && (
        (window.outerWidth - window.innerWidth) > threshold ||
        (window.outerHeight - window.innerHeight) > threshold
    )) {
        showDevToolsWarning();
        return true;
    }
    return false;
}

// Listen for resize events (often accompany dev tools opening/closing/docking)
if (typeof window !== 'undefined') {
    window.addEventListener('resize', () => {
        ongoingCheckDevTools();
    });
}

// Enhanced debugger check using console.log behavior with a special getter
let devtoolsViaConsoleLog = false;
const imageElementForConsoleCheck = new Image();
Object.defineProperty(imageElementForConsoleCheck, 'id', {
  get: () => {
    devtoolsViaConsoleLog = true;
    // No need to call showDevToolsWarning directly here, let the interval handle it
    // to avoid multiple rapid calls if console is spammed.
  }
});

// Periodic check combining multiple methods
if (typeof window !== 'undefined') {
    setInterval(() => {
        // Reset flag for console log check
        devtoolsViaConsoleLog = false;
        // The next line, when devtools are open and possibly inspecting console output,
        // will trigger the 'id' getter on imageElementForConsoleCheck.
        // Use console.dirxml or similar that forces property access if console.log is optimized.
        if (typeof console.dirxml === 'function') {
            console.dirxml(imageElementForConsoleCheck);
        } else {
            console.log(imageElementForConsoleCheck); // Fallback
        }
        if (console.clear) console.clear(); // Try to clear the console to hide the log

        // Debugger timing check (less aggressive interval than immediate check)
        const before = new Date().getTime();
        debugger;
        const after = new Date().getTime();

        if ((after - before) > 100 || devtoolsViaConsoleLog || ongoingCheckDevTools()) {
            showDevToolsWarning();
        }
    }, 2500); // Check every 2.5 seconds
}
