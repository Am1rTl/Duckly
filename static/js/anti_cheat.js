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


// Function to display warning and clear content
function showDevToolsWarning() {
    // Remove existing content
    document.body.innerHTML = '';

    // Create warning message elements
    const warningDiv = document.createElement('div');
    warningDiv.style.position = 'fixed';
    warningDiv.style.top = '0';
    warningDiv.style.left = '0';
    warningDiv.style.width = '100%';
    warningDiv.style.height = '100%';
    warningDiv.style.backgroundColor = 'rgba(0,0,0,0.9)';
    warningDiv.style.color = 'white';
    warningDiv.style.zIndex = '9999';
    warningDiv.style.display = 'flex';
    warningDiv.style.flexDirection = 'column';
    warningDiv.style.justifyContent = 'center';
    warningDiv.style.alignItems = 'center';
    warningDiv.style.textAlign = 'center';
    warningDiv.style.fontSize = '24px';
    warningDiv.style.fontFamily = 'sans-serif';

    const warningTitle = document.createElement('h1');
    warningTitle.textContent = 'Developer Tools Detected!';
    warningTitle.style.fontSize = '48px';
    warningTitle.style.marginBottom = '20px';

    const warningText = document.createElement('p');
    warningText.textContent = 'Please close the developer tools to continue.';
    warningText.style.lineHeight = '1.6';

    const warningIcon = document.createElement('p');
    warningIcon.textContent = '⚠️';
    warningIcon.style.fontSize = '60px';
    warningIcon.style.marginTop = '30px';

    warningDiv.appendChild(warningTitle);
    warningDiv.appendChild(warningText);
    warningDiv.appendChild(warningIcon);
    document.body.appendChild(warningDiv);
}

// Function to check for developer tools
function checkDevTools() {
    const threshold = 160; // Height/width difference threshold

    // Check 1: Window size difference
    if (window.outerWidth - window.innerWidth > threshold ||
        window.outerHeight - window.innerHeight > threshold) {
        showDevToolsWarning();
        return true; // Dev tools detected
    }

    // Check 2: Debugger statement timing
    // This is more of a one-time check or needs careful handling if used in setInterval
    // For now, focusing on the resize event and initial load primarily for this check.
    // A more robust debugger check would involve measuring execution time.

    // Fallback for browsers that might not trigger resize or where dimensions are less reliable
    // (e.g., undocked dev tools). We can also check if an element with a specific ID used
    // by dev tools exists, but this is highly browser-dependent and fragile.

    // A simple console check (less reliable, as console can be open without full dev tools UI)
    // console.profile();
    // console.profileEnd();
    // if (console.clear) console.clear(); // Attempt to clear, some dev tools might override this.
    // if (console._commandLineAPI || console._inspectorCommandLineAPI) { // Non-standard, might work in some
    //    showDevToolsWarning();
    //    return true;
    // }

    return false; // Dev tools not detected by this check
}

// Initial check
if (checkDevTools()) {
    // Dev tools were open on load
}

// Periodically check for dev tools
// More aggressive check:
// setInterval(checkDevTools, 1000);

// Less aggressive check: Listen for resize events which often accompany dev tools opening/closing
window.addEventListener('resize', () => {
    checkDevTools();
});

// Enhanced debugger check (more reliable but can be intensive)
let devtoolsOpen = false;
const element = new Image();
Object.defineProperty(element, 'id', {
  get: () => {
    devtoolsOpen = true;
    // Optionally call showDevToolsWarning() directly here if immediate action is desired
    // However, it's better to let the interval handle it for consistency
  }
});

setInterval(() => {
  devtoolsOpen = false;
  // console.log(element); // This line triggers the getter if devtools are open and inspecting console
  // The following is a more common pattern for this trick:
  const before = new Date().getTime();
  debugger; // This will pause execution if dev tools are open
  const after = new Date().getTime();
  if (after - before > 100) { // If execution paused for more than 100ms
    devtoolsOpen = true;
  }

  if (devtoolsOpen) {
    showDevToolsWarning();
  }
  checkDevTools(); // Also run the window size check
}, 2000); // Check every 2 seconds
