document.addEventListener('DOMContentLoaded', function() {
    const wordsDataElement = document.getElementById('mcSingleWordsData');
    const timerDisplay = document.getElementById('timer');
    const testForm = document.getElementById('test-form');
    const progressBar = document.getElementById('progress-bar');
    const prevButton = document.getElementById('prev-btn');
    const nextButton = document.getElementById('next-btn');
    const submitButton = document.getElementById('submit-btn');

    if (!wordsDataElement || !timerDisplay || !testForm || !progressBar || !prevButton || !nextButton || !submitButton) {
        console.error("One or more critical elements for the multiple choice test are missing.");
        if(progressBar) progressBar.innerHTML = '<p style="text-align:center; color:var(--danger);">Ошибка загрузки теста: отсутствует критический элемент.</p>';
        if(timerDisplay) timerDisplay.style.display = 'none';
        // Disable all controls if essential elements are missing
        if(prevButton) prevButton.disabled = true;
        if(nextButton) nextButton.disabled = true;
        if(submitButton) { submitButton.disabled = true; submitButton.style.display = 'none'; }
        return;
    }

    let wordsData;
    try {
        wordsData = JSON.parse(wordsDataElement.textContent);
    } catch (e) {
        console.error("Error parsing wordsData JSON:", e);
        progressBar.innerHTML = '<p style="text-align:center; color:var(--danger);">Ошибка загрузки данных теста.</p>';
        timerDisplay.style.display = 'none';
        prevButton.disabled = true;
        nextButton.disabled = true;
        if(submitButton) { submitButton.disabled = true; submitButton.style.display = 'none'; }
        return;
    }

    const timeLimit = parseInt(timerDisplay.dataset.timeLimit || '0', 10);
    let timeLeft = timeLimit > 0 ? timeLimit * 60 : 0;
    let timerInterval;
    let currentIndex = 0;

    let userAnswersArrayLength = 0;
    if (wordsData && wordsData.length > 0) {
        userAnswersArrayLength = wordsData.length;
    }
    const userAnswers = new Array(userAnswersArrayLength).fill(null);

    if (!wordsData || wordsData.length === 0) {
        console.error("Test data (wordsData) is missing or empty after parsing. Test cannot proceed.");
        progressBar.innerHTML = '<p style="text-align:center; color:var(--danger);">Тест не может быть загружен: нет данных для вопросов.</p>';
        timerDisplay.style.display = 'none';
        prevButton.disabled = true;
        nextButton.disabled = true;
        if(submitButton) { submitButton.disabled = true; submitButton.style.display = 'none'; }
        // Hide all word containers
        document.querySelectorAll('.word-container').forEach(container => {
            container.style.display = 'none';
        });
        return;
    }

    startTimer();
    showWord(0);

    function startTimer() {
        if (timeLimit > 0) {
            updateTimerDisplay();
            timerInterval = setInterval(updateTimer, 1000);
        } else {
            timerDisplay.style.display = 'none';
        }
    }

    function updateTimerDisplay() {
        const minutes = Math.floor(timeLeft / 60);
        const seconds = timeLeft % 60;
        const timeLeftSpan = document.getElementById('time-left');
        if(timeLeftSpan) {
            timeLeftSpan.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }
    }

    function updateTimer() {
        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            if (!testForm.submitted) {
                 testForm.submitted = true; // Mark as submitted
                 testForm.submit(); // Auto-submit
            }
            return;
        }
        timeLeft--;
        updateTimerDisplay();
    }

    function updateProgressBar() {
        const items = progressBar.querySelectorAll('.progress-item');
        items.forEach((item, index) => {
            item.classList.remove('current', 'completed', 'answered');
            if (userAnswers[index] !== null) {
                item.classList.add('answered');
            }
            if (index === currentIndex) {
                item.classList.add('current');
            } else if (index < currentIndex && userAnswers[index] !== null) {
                 item.classList.add('completed');
            }
        });

        prevButton.disabled = currentIndex === 0;
        if (currentIndex === wordsData.length - 1) {
            nextButton.style.display = 'none';
            if(submitButton) submitButton.style.display = 'inline-flex';
        } else {
            nextButton.style.display = 'inline-flex';
            if(submitButton) submitButton.style.display = 'none';
        }
    }

    function showWord(index) {
        document.querySelectorAll('.word-container').forEach(container => {
            container.style.display = 'none';
        });
        const currentContainer = document.querySelector(`.word-container[data-index="${index}"]`);
        if (currentContainer) {
             currentContainer.style.display = 'block';
        }
        currentIndex = index;
        updateProgressBar();

        if (wordsData[currentIndex]) { // Check if wordsData[currentIndex] is defined
            const wordId = wordsData[currentIndex].id;
            const selectedValue = userAnswers[currentIndex];
            document.querySelectorAll(`.option-btn[data-word-id="${wordId}"]`).forEach(btn => {
                btn.classList.remove('selected');
                if (btn.dataset.value === selectedValue) {
                    btn.classList.add('selected');
                }
            });
        } else {
            console.warn(`Attempted to show word at invalid index: ${index}`);
        }
    }

    prevButton.addEventListener('click', () => {
        if (currentIndex > 0) {
            showWord(currentIndex - 1);
        }
    });

    nextButton.addEventListener('click', () => {
        if (userAnswers[currentIndex] === null) {
             alert('Пожалуйста, выберите ответ.');
             return;
        }
        if (currentIndex < wordsData.length - 1) {
            showWord(currentIndex + 1);
        }
    });

    progressBar.querySelectorAll('.progress-item').forEach(item => {
        item.addEventListener('click', () => {
            const index = parseInt(item.dataset.index);
            if (userAnswers[index] !== null || (index === currentIndex + 1 && userAnswers[currentIndex] !== null) || index === currentIndex ) {
                 if (userAnswers[currentIndex] !== null || index <= currentIndex) {
                    showWord(index);
                 } else {
                    alert('Пожалуйста, сначала ответьте на текущий вопрос.');
                 }
            } else if (index > currentIndex && userAnswers[currentIndex] === null) {
                 alert('Пожалуйста, сначала ответьте на текущий вопрос.');
            }
        });
    });

    document.querySelectorAll('.option-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const wordId = btn.dataset.wordId;
            const value = btn.dataset.value;

            const hiddenInput = document.getElementById(`answer-input-${wordId}`);
            if (hiddenInput) {
                hiddenInput.value = value;
            }

            userAnswers[currentIndex] = value;

            document.querySelectorAll(`.option-btn[data-word-id="${wordId}"]`).forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            updateProgressBar();
        });
    });

    testForm.addEventListener('submit', (e) => {
        if (testForm.submitted) {
            e.preventDefault();
            return;
        }

        const allAnswered = userAnswers.every(answer => answer !== null);
        if (!allAnswered) {
            if (!confirm('Вы не ответили на все вопросы. Вы уверены, что хотите завершить тест?')) {
                e.preventDefault();
                return false;
            }
        }

        wordsData.forEach((word, index) => {
            const hiddenInput = document.getElementById(`answer-input-${word.id}`);
            if (hiddenInput && userAnswers[index] !== null) {
                hiddenInput.value = userAnswers[index];
            } else if (hiddenInput) {
                hiddenInput.value = "";
            }
        });
        testForm.submitted = true; // Mark as submitted
        if(submitButton){
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Отправка...';
        }
        if(prevButton) prevButton.disabled = true;
        if(nextButton) nextButton.disabled = true;
    });
});
