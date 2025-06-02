document.addEventListener('DOMContentLoaded', function() {
    const testForm = document.getElementById('fillWordTestForm');
    if (!testForm) {
        console.error("Fill Word test form not found!");
        return;
    }

    const testDbId = testForm.dataset.testDbId;
    const wordsContainer = document.getElementById('test-questions-container');
    const loadingMessageElement = wordsContainer ? wordsContainer.querySelector('.loading-message') : null;
    const noWordsMessageContainer = document.getElementById('no-words-message-container');
    const submitButton = document.getElementById('submit-test-button');
    const timerDisplay = document.getElementById('timer');
    const isTeacherPreview = testForm.dataset.isTeacherPreview === 'true';


    if (!wordsContainer || !loadingMessageElement || !noWordsMessageContainer || !submitButton || !timerDisplay) {
        console.error("One or more required page elements for Fill Word test are missing.");
        if(timerDisplay) timerDisplay.textContent = "Ошибка конфигурации страницы.";
        if(wordsContainer) wordsContainer.innerHTML = "<p>Ошибка конфигурации страницы.</p>";
        if(loadingMessageElement) loadingMessageElement.style.display = 'none';
        if(submitButton) submitButton.style.display = 'none';
        return;
    }

    function hideMainControls() {
        if(submitButton) submitButton.style.display = 'none';
    }

    if (window.antiCheatInitialCheckPassed === true) {
        loadFillWordData();
    } else {
        console.warn("Anti-cheat initial check did not pass for fill_word test. Test data will not be loaded.");
        if (loadingMessageElement) loadingMessageElement.style.display = 'none';
        const acWarningOverlay = document.querySelector('div[style*="z-index: 2147483647"]');
        if (!acWarningOverlay && wordsContainer) {
             wordsContainer.innerHTML = '<p style="text-align:center; color: var(--danger); padding: 20px; font-size: 1.1em;">Проверка безопасности не пройдена. Загрузка теста отменена.</p>';
        }
        hideMainControls();
        if (noWordsMessageContainer) {
            const backLink = document.createElement('a');
            backLink.href = "/tests";
            backLink.className = "btn btn-secondary mt-3";
            backLink.textContent = "Вернуться к списку тестов";
            noWordsMessageContainer.innerHTML = '';
            noWordsMessageContainer.appendChild(backLink);
            noWordsMessageContainer.style.textAlign = 'center';
        }
    }

    async function loadFillWordData() {
        if (!testDbId) {
            console.error("Test DB ID is missing.");
            wordsContainer.innerHTML = '<p style="text-align:center; color: var(--danger);">Ошибка конфигурации: ID теста отсутствует.</p>';
            if(loadingMessageElement) loadingMessageElement.style.display = 'none';
            hideMainControls();
            return;
        }

        try {
            const response = await fetch(`/api/test/${testDbId}/fill_word_words`);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(`Network response was not ok: ${response.status} ${response.statusText}. ${errorData.error || ''}`);
            }
            const data = await response.json();

            if(loadingMessageElement) loadingMessageElement.style.display = 'none';
            wordsContainer.innerHTML = '';

            if (data.words && data.words.length > 0) {
                data.words.forEach((wordData, index) => {
                    renderFillWordQuestion(wordData, index, wordsContainer);
                });
                if(submitButton) submitButton.style.display = 'block';
                initializeTimerAndSubmitLogic();
            } else {
                noWordsMessageContainer.innerHTML = '<p style="text-align:center; color: var(--secondary);">В этом тесте нет вопросов для отображения.</p>';
                hideMainControls();
                const backLink = document.createElement('a');
                backLink.href = "/tests";
                backLink.className = "btn btn-secondary mt-3";
                backLink.textContent = "Вернуться к списку тестов";
                noWordsMessageContainer.appendChild(backLink);
                noWordsMessageContainer.style.textAlign = 'center';
            }
        } catch (error) {
            console.error("Failed to load or render fill_word test words:", error);
            if(loadingMessageElement) loadingMessageElement.style.display = 'none';
            wordsContainer.innerHTML = `<p style="text-align:center; color: var(--danger);">Ошибка загрузки вопросов: ${error.message}. Попробуйте обновить страницу.</p>`;
            hideMainControls();
            const backLinkOnError = document.createElement('a');
            backLinkOnError.href = "/tests";
            backLinkOnError.className = "btn btn-secondary mt-3";
            backLinkOnError.textContent = "Вернуться к списку тестов";
            wordsContainer.appendChild(backLinkOnError);
        }
    }

    function renderFillWordQuestion(wordData, index, container) {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'question-item shadow-sm';

        const questionNumberP = document.createElement('p');
        questionNumberP.className = 'mb-1';
        questionNumberP.innerHTML = `<strong>Вопрос ${index + 1}:</strong>`;
        itemDiv.appendChild(questionNumberP);

        const promptP = document.createElement('p');
        promptP.className = 'prompt';
        promptP.textContent = wordData.question_prompt;
        itemDiv.appendChild(promptP);

        if (wordData.instruction) {
            const instructionSmall = document.createElement('small');
            instructionSmall.className = 'instruction';
            instructionSmall.innerHTML = `<em>${wordData.instruction}</em>`;
            itemDiv.appendChild(instructionSmall);
        }

        const inputDiv = document.createElement('div');
        inputDiv.className = 'mt-2';
        const inputEl = document.createElement('input');
        inputEl.type = 'text';
        inputEl.name = `answer_${wordData.id}`;
        inputEl.id = `answer_${wordData.id}`;
        inputEl.className = 'form-control';
        inputEl.required = true;
        inputEl.autocomplete = 'off';
        inputEl.setAttribute('aria-label', `Ответ на вопрос ${index + 1}`);
        inputDiv.appendChild(inputEl);
        itemDiv.appendChild(inputDiv);

        container.appendChild(itemDiv);
    }

    function initializeTimerAndSubmitLogic() {
        const timeLimitMinutes = parseInt(timerDisplay.dataset.timeLimit || '0', 10);
        let remainingTimeSeconds = parseInt(timerDisplay.dataset.remainingTimeSeconds || '-1', 10);
        let timerInterval;
        let formSubmittedByCode = false;

        function submitFormLogic() {
            if (formSubmittedByCode) return;
            formSubmittedByCode = true;

            clearInterval(timerInterval);
            timerDisplay.textContent = "Время вышло!";
            setTimeout(() => {
                 if (typeof testForm.submit === 'function' && !testForm.submitted) {
                    testForm.submitted = true;
                    if (submitButton) {
                        submitButton.disabled = true;
                        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Отправка...';
                    }
                    testForm.submit();
                }
            }, 500);
        }

        if (timeLimitMinutes > 0 && !isTeacherPreview) {
            let timeLeft;
            if (remainingTimeSeconds >= 0) {
                timeLeft = remainingTimeSeconds;
            } else {
                timeLeft = timeLimitMinutes * 60;
            }

            if (timeLeft === 0 && remainingTimeSeconds !== -1) {
                 submitFormLogic();
            } else if (timeLeft > 0) {
                const updateTimer = () => {
                    if (formSubmittedByCode) { clearInterval(timerInterval); return; }
                    const minutes = Math.floor(timeLeft / 60);
                    let seconds = timeLeft % 60;
                    seconds = seconds < 10 ? '0' + seconds : seconds;
                    timerDisplay.textContent = `Осталось времени: ${minutes}:${seconds}`;

                    if (timeLeft <= 0) {
                       submitFormLogic();
                    }
                    timeLeft--;
                };
                updateTimer();
                timerInterval = setInterval(updateTimer, 1000);
            } else {
                 timerDisplay.textContent = "Время: Без ограничений";
            }
        } else if (!isTeacherPreview) {
            timerDisplay.textContent = "Время: Без ограничений";
        } else {
            timerDisplay.style.display = 'none';
        }

        testForm.addEventListener('submit', function(event) {
            if (testForm.submitted) {
                event.preventDefault();
                return;
            }
            let allAnswered = true;
            if (wordsContainer.querySelector('.question-item')) {
                const inputs = testForm.querySelectorAll('input[type="text"].form-control');
                for (const input of inputs) {
                    if (input.name.startsWith('answer_') && input.value.trim() === '') {
                        allAnswered = false;
                        break;
                    }
                }
                if (!allAnswered) {
                    if (!confirm('Вы не ответили на все вопросы. Вы уверены, что хотите завершить тест?')) {
                        event.preventDefault();
                        return;
                    }
                }
            }

            testForm.submitted = true;
            formSubmittedByCode = true;
            clearInterval(timerInterval);

            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Отправка...';
            }
        });
    }
});
