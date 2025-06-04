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

function showPrintSaveWarning(action) {
    // Создаем временное предупреждение
    const warningHTML = `
        <div id="print-save-warning" style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background-color: rgba(220, 53, 69, 0.95); color: white; z-index: 2147483646; padding: 30px; border-radius: 15px; text-align: center; font-size: 18px; font-family: 'Poppins', sans-serif; box-shadow: 0 10px 30px rgba(0,0,0,0.3); max-width: 400px;">
            <div style="font-size: 40px; margin-bottom: 15px;">🚫</div>
            <h2 style="font-size: 24px; margin-bottom: 10px; font-weight: 600;">Действие запрещено!</h2>
            <p style="font-size: 16px; line-height: 1.4; margin-bottom: 20px;">Попытка выполнить "${action}" заблокирована для защиты содержимого теста.</p>
            <p style="font-size: 14px; color: #ffcccc;">Это предупреждение исчезнет через 3 секунды.</p>
        </div>
    `;
    
    // Удаляем предыдущее предупреждение, если оно есть
    const existingWarning = document.getElementById('print-save-warning');
    if (existingWarning) {
        existingWarning.remove();
    }
    
    // Добавляем новое предупреждение
    const warningDiv = document.createElement('div');
    warningDiv.innerHTML = warningHTML;
    document.body.appendChild(warningDiv);
    
    // Автоматически удаляем предупреждение через 3 секунды
    setTimeout(() => {
        const warning = document.getElementById('print-save-warning');
        if (warning) {
            warning.style.opacity = '0';
            warning.style.transition = 'opacity 0.5s ease';
            setTimeout(() => warning.remove(), 500);
        }
    }, 3000);
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
    let printSaveBlocked = false;
    
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
    
    // БЛОКИРОВКА ПЕЧАТИ И СОХРАНЕНИЯ
    // Ctrl+P / Cmd+P (Print)
    if ((event.ctrlKey || event.metaKey) && (event.key === 'p' || event.key === 'P' || event.keyCode === 80)) {
        printSaveBlocked = true;
        showPrintSaveWarning('печать');
    }
    // Ctrl+S / Cmd+S (Save)
    if ((event.ctrlKey || event.metaKey) && (event.key === 's' || event.key === 'S' || event.keyCode === 83)) {
        printSaveBlocked = true;
        showPrintSaveWarning('сохранение');
    }
    // Ctrl+Shift+S / Cmd+Shift+S (Save As)
    if ((event.ctrlKey || event.metaKey) && event.shiftKey && (event.key === 's' || event.key === 'S' || event.keyCode === 83)) {
        printSaveBlocked = true;
        showPrintSaveWarning('сохранение');
    }
    // Ctrl+A / Cmd+A (Select All) - блокируем для предотвращения копирования всего
    if ((event.ctrlKey || event.metaKey) && (event.key === 'a' || event.key === 'A' || event.keyCode === 65)) {
        printSaveBlocked = true;
        showPrintSaveWarning('выделение текста');
    }

    if (devToolsOpened) {
        event.preventDefault();
        showDevToolsWarning();
        return false;
    }
    
    if (printSaveBlocked) {
        event.preventDefault();
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

// --- ДОПОЛНИТЕЛЬНАЯ ЗАЩИТА ОТ ПЕЧАТИ И СОХРАНЕНИЯ ---

// Блокировка события печати
window.addEventListener('beforeprint', function(event) {
    event.preventDefault();
    showPrintSaveWarning('печать');
    return false;
});

window.addEventListener('afterprint', function(event) {
    event.preventDefault();
    showPrintSaveWarning('печать');
    return false;
});

// Переопределяем функцию print
if (typeof window.print === 'function') {
    window.print = function() {
        showPrintSaveWarning('печать');
        return false;
    };
}

// Блокировка через медиа-запросы CSS (добавляем стили динамически)
function addPrintBlockingCSS() {
    const style = document.createElement('style');
    style.type = 'text/css';
    style.innerHTML = `
        @media print {
            * {
                display: none !important;
                visibility: hidden !important;
                opacity: 0 !important;
            }
            body::before {
                content: "ПЕЧАТЬ ЗАПРЕЩЕНА! Содержимое теста защищено от копирования.";
                display: block !important;
                visibility: visible !important;
                opacity: 1 !important;
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-size: 24px;
                font-weight: bold;
                color: red;
                text-align: center;
                z-index: 9999;
                background: white;
                padding: 50px;
                border: 3px solid red;
            }
        }
        
        /* Дополнительная защита от выделения */
        * {
            -webkit-user-select: none !important;
            -moz-user-select: none !important;
            -ms-user-select: none !important;
            user-select: none !important;
            -webkit-touch-callout: none !important;
            -webkit-tap-highlight-color: transparent !important;
        }
        
        /* Блокировка перетаскивания изображений */
        img {
            -webkit-user-drag: none !important;
            -khtml-user-drag: none !important;
            -moz-user-drag: none !important;
            -o-user-drag: none !important;
            user-drag: none !important;
            pointer-events: none !important;
        }
    `;
    
    // Добавляем стили в head
    if (document.head) {
        document.head.appendChild(style);
    } else {
        // Если head еще не готов, ждем
        document.addEventListener('DOMContentLoaded', function() {
            if (document.head) {
                document.head.appendChild(style);
            }
        });
    }
}

// Применяем CSS защиту
addPrintBlockingCSS();

// Дополнительная защита - блокировка drag and drop
document.addEventListener('dragstart', function(event) {
    event.preventDefault();
    return false;
});

document.addEventListener('drop', function(event) {
    event.preventDefault();
    return false;
});

document.addEventListener('dragover', function(event) {
    event.preventDefault();
    return false;
});

// Блокировка сохранения изображений
document.addEventListener('contextmenu', function(event) {
    if (event.target.tagName === 'IMG') {
        event.preventDefault();
        showPrintSaveWarning('сохранение изображения');
        return false;
    }
});

// Мониторинг попыток изменения CSS через DevTools
if (typeof window !== 'undefined') {
    setInterval(function() {
        // Проверяем, не были ли удалены наши стили защиты
        const styles = document.querySelectorAll('style');
        let hasProtectionCSS = false;
        
        styles.forEach(function(style) {
            if (style.innerHTML && style.innerHTML.includes('@media print')) {
                hasProtectionCSS = true;
            }
        });
        
        // Если защитные стили были удалены, добавляем их снова
        if (!hasProtectionCSS) {
            addPrintBlockingCSS();
        }
    }, 5000); // Проверяем каждые 5 секунд
}

// Блокировка скриншотов (частично) - предупреждение при потере фокуса
let isTestPage = window.location.pathname.includes('/test/') || 
                 window.location.pathname.includes('/take_test/') ||
                 document.title.toLowerCase().includes('тест');

if (isTestPage) {
    let focusLostCount = 0;
    
    window.addEventListener('blur', function() {
        focusLostCount++;
        if (focusLostCount > 2) {
            showPrintSaveWarning('подозрительная активность (возможная попытка скриншота)');
        }
    });
    
    // Сброс счетчика при возвращении фокуса
    window.addEventListener('focus', function() {
        setTimeout(function() {
            focusLostCount = Math.max(0, focusLostCount - 1);
        }, 10000); // Уменьшаем счетчик через 10 секунд
    });
}
