document.addEventListener('DOMContentLoaded', function() {
    const flashcardDataElement = document.getElementById('flashcardData');
    const flashcardContainer = document.getElementById('flashcard-container'); // Updated to new container ID
    const cardFront = document.querySelector('.flashcard .card-front');
    const cardBack = document.querySelector('.flashcard .card-back');
    const prevButton = document.getElementById('prevCard');
    const nextButton = document.getElementById('nextCard');
    const flipButton = document.getElementById('flipCard');
    const progressDisplay = document.getElementById('flashcard-progress');
    const srsControlsContainer = document.getElementById('srs-controls');
    const srsButtons = {
        again: document.getElementById('srs-again'),
        hard: document.getElementById('srs-hard'),
        good: document.getElementById('srs-good'),
        easy: document.getElementById('srs-easy')
    };

    let words = [];
    let moduleName = '';

    if (flashcardDataElement) {
        try {
            const jsonData = JSON.parse(flashcardDataElement.textContent);
            words = jsonData.words || [];
            moduleName = jsonData.moduleName || 'Модуль'; // Fallback title
        } catch (e) {
            console.error("Error parsing flashcard data:", e);
            if (cardFront) cardFront.textContent = 'Ошибка загрузки слов';
        }
    } else {
        if (cardFront) cardFront.textContent = 'Нет данных для карточек';
    }

    let currentCardIndex = 0;
    // isFlipped state is implicitly handled by the 'is-flipped' class on flashcardContainer

    function showCard(index) {
        if (!words || words.length === 0) {
            if (cardFront) cardFront.textContent = 'Нет слов в этом модуле.';
            if (cardBack) cardBack.textContent = '';
            if (progressDisplay) progressDisplay.textContent = `0/0 | ${moduleName}`;
            if (prevButton) prevButton.disabled = true;
            if (nextButton) nextButton.disabled = true;
            if (flipButton) flipButton.disabled = true;
            return;
        }

        const card = words[index];
        if (cardFront) cardFront.textContent = card.word;
        if (cardBack) cardBack.textContent = card.perevod;

        if (flashcardContainer) flashcardContainer.classList.remove('is-flipped');

        if (progressDisplay) progressDisplay.textContent = `Карточка ${index + 1} из ${words.length}`;

        if (prevButton) prevButton.disabled = index === 0;
        if (nextButton) nextButton.disabled = index === words.length - 1;
        if (flipButton) flipButton.disabled = false;
        if (flipButton) flipButton.style.display = 'inline-flex';
        if (prevButton) prevButton.style.display = 'inline-flex'; // Show/hide based on index later
        if (nextButton) nextButton.style.display = 'inline-flex';
        if (srsControlsContainer) srsControlsContainer.style.display = 'none';
        updateNavButtonVisibility();
    }

    function updateNavButtonVisibility() {
        if (!words || words.length === 0) return;
        if (prevButton) prevButton.disabled = currentCardIndex === 0;
        if (nextButton) nextButton.disabled = currentCardIndex === words.length - 1;
    }

    function handleFlip() {
        if (!flashcardContainer || words.length === 0) return;
        flashcardContainer.classList.toggle('is-flipped');
        const isNowFlipped = flashcardContainer.classList.contains('is-flipped');
        if (isNowFlipped) {
            if (flipButton) flipButton.style.display = 'none';
            if (prevButton) prevButton.style.display = 'none';
            if (nextButton) nextButton.style.display = 'none';
            if (srsControlsContainer) srsControlsContainer.style.display = 'flex';
        } else { // Should not happen if SRS buttons are clicked, as they move to next card
            if (flipButton) flipButton.style.display = 'inline-flex';
            if (prevButton) prevButton.style.display = 'inline-flex';
            if (nextButton) nextButton.style.display = 'inline-flex';
            if (srsControlsContainer) srsControlsContainer.style.display = 'none';
            updateNavButtonVisibility();
        }
    }

    if (flipButton) {
        flipButton.addEventListener('click', handleFlip);
    }

    if (flashcardContainer) {
        flashcardContainer.addEventListener('click', (event) => {
            if (event.target.closest('button') || srsControlsContainer.style.display === 'flex') return;
            if (words.length > 0) {
                 handleFlip();
            }
        });
    }

    if (prevButton) {
        prevButton.addEventListener('click', () => {
            if (currentCardIndex > 0) {
                currentCardIndex--;
                showCard(currentCardIndex);
            }
        });
    }

    if (nextButton) {
        nextButton.addEventListener('click', () => {
            if (currentCardIndex < words.length - 1) {
                currentCardIndex++;
                showCard(currentCardIndex);
            }
        });
    }

    Object.values(srsButtons).forEach(button => {
        if (button) {
            button.addEventListener('click', function() {
                if (!words || words.length === 0) return;

                const wordId = words[currentCardIndex].id;
                const quality = this.dataset.quality;

                // Disable SRS buttons to prevent multiple clicks
                Object.values(srsButtons).forEach(btn => btn.disabled = true);


                fetch('/games/flashcards/update_review', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        // Add CSRF token header here if/when implemented
                    },
                    body: JSON.stringify({ word_id: wordId, quality: quality })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Optionally, update the local word data with new review info if needed for immediate sorting/filtering
                        // words[currentCardIndex].next_review_at = data.next_review_date;
                        // words[currentCardIndex].interval_days = data.next_review_in_days;
                        // words[currentCardIndex].is_new = false; // No longer new

                        currentCardIndex++;
                        if (currentCardIndex < words.length) {
                            showCard(currentCardIndex);
                        } else {
                            if (cardFront) cardFront.textContent = 'Модуль завершен!';
                            if (cardBack) cardBack.textContent = '';
                            if (flashcardContainer) flashcardContainer.classList.remove('is-flipped');
                            if (progressDisplay) progressDisplay.textContent = `Завершено: ${words.length}/${words.length}`;
                            if (flipButton) flipButton.style.display = 'none';
                            if (prevButton) prevButton.style.display = 'none';
                            if (nextButton) nextButton.style.display = 'none';
                            if (srsControlsContainer) srsControlsContainer.style.display = 'none';
                            // Maybe show a "practice again" or "select module" button more prominently
                        }
                    } else {
                        console.error('Error updating review:', data.error);
                        alert(`Ошибка обновления карточки: ${data.error || 'Неизвестная ошибка'}`);
                    }
                })
                .catch(error => {
                    console.error('Fetch error:', error);
                    alert('Сетевая ошибка при обновлении карточки.');
                })
                .finally(() => {
                    // Re-enable SRS buttons if not moving to next card or completion
                    // This might not be needed if we always move to next or complete
                     Object.values(srsButtons).forEach(btn => btn.disabled = false);
                });
            });
        }
    });

    // Add keyboard navigation for flashcards
    document.addEventListener('keydown', function(event) {
        if (document.activeElement && (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'BUTTON')) {
            return;
        }

        const srsVisible = srsControlsContainer && srsControlsContainer.style.display === 'flex';

        if (srsVisible) {
            switch (event.key) {
                case '0': if (srsButtons.again) srsButtons.again.click(); break;
                case '1': if (srsButtons.hard) srsButtons.hard.click(); break;
                case '2': if (srsButtons.good) srsButtons.good.click(); break;
                case '3': if (srsButtons.easy) srsButtons.easy.click(); break;
            }
        } else {
            switch (event.key) {
                case 'ArrowLeft':
                    if (prevButton && !prevButton.disabled) prevButton.click();
                    break;
                case 'ArrowRight':
                    if (nextButton && !nextButton.disabled) nextButton.click();
                    break;
                case ' ':
                case 'ArrowUp':
                case 'ArrowDown':
                     if (flipButton && !flipButton.disabled && flipButton.style.display !== 'none') {
                        flipButton.click();
                        event.preventDefault();
                     }
                    break;
            }
        }
    });

    showCard(currentCardIndex);
});
