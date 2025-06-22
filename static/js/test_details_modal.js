// test_details_modal.js
// Открывает модальное окно с деталями теста по клику на кнопку "Детали"
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.teacher-details-btn-style').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            // Allow the anchor default navigation to work or explicitly redirect
            const testLink = btn.getAttribute('data-test-link');
            if (!testLink) return;
            window.location.href = `/tests/${testLink}/details`;
        });
    });
});

