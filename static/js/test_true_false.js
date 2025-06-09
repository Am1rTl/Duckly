document.addEventListener('DOMContentLoaded', function() {
    const testForm = document.getElementById('trueFalseTestForm');
    if (!testForm) {
        console.error("True/False test form not found!");
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
        console.error("One or more required page elements for True/False test are missing.");
        if(timerDisplay) timerDisplay.textContent = "Ошибка конфигурации страницы.";
        if(wordsContainer) wordsContainer.innerHTML = "<p>Ошибка конфигурации страницы.</p>";
        if(loadingMessageElement) loadingMessageElement.style.display = 'none';
        if(submitButton) submitButton.style.display = 'none';
        return;
    }

    function hideMainControls() {
        if(submitButton) submitButton.style.display = 'none';
        // Add other controls specific to this test type if they need hiding
    }

    if (window.antiCheatInitialCheckPassed === true) {
        loadTrueFalseWords();
    } else {
        console.warn("Anti-cheat initial check did not pass for true_false test. Test data will not be loaded.");
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
            noWordsMessageContainer.innerHTML = ''; // Clear previous messages
            noWordsMessageContainer.appendChild(backLink);
            noWordsMessageContainer.style.textAlign = 'center'; // Center the button
        }
    }


    async function loadTrueFalseWords() {
        if (!testDbId) {
            console.error("Test DB ID is missing.");
            wordsContainer.innerHTML = '<p style="text-align:center; color: var(--danger);">Ошибка конфигурации: ID теста отсутствует.</p>';
            loadingMessageElement.style.display = 'none';
            hideMainControls();
            return;
        }

        try {
            const response = await fetch(`/api/test/${testDbId}/true_false_words`);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(`Network response was not ok: ${response.status} ${response.statusText}. ${errorData.error || ''}`);
            }
            const data = await response.json();

            loadingMessageElement.style.display = 'none';
            wordsContainer.innerHTML = '';

            if (data.words && data.words.length > 0) {
                data.words.forEach((wordData, index) => {
                    renderTrueFalseWord(wordData, index, wordsContainer);
                });
                submitButton.style.display = 'block';
                initializeTimerAndSubmitLogic(); // Setup timer and submit after words are loaded
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
            console.error("Failed to load or render true_false test words:", error);
            loadingMessageElement.style.display = 'none';
            wordsContainer.innerHTML = `<p style="text-align:center; color: var(--danger);">Ошибка загрузки вопросов: ${error.message}. Попробуйте обновить страницу.</p>`;
            hideMainControls();
            const backLinkOnError = document.createElement('a');
            backLinkOnError.href = "/tests";
            backLinkOnError.className = "btn btn-secondary mt-3";
            backLinkOnError.textContent = "Вернуться к списку тестов";
            wordsContainer.appendChild(backLinkOnError); // Append to main container as noWords might not be suitable
        }
    }

    function renderTrueFalseWord(wordData, index, container) {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'question-item shadow-sm';

        const questionNumberP = document.createElement('p');
        questionNumberP.className = 'mb-1';
        questionNumberP.innerHTML = `<strong>Вопрос ${index + 1}:</strong>`;
        itemDiv.appendChild(questionNumberP);

        const statementP = document.createElement('p');
        statementP.textContent = wordData.statement;
        itemDiv.appendChild(statementP);

        if (wordData.prompt && wordData.prompt.toLowerCase() !== "верно или неверно?") {
            const hintSmall = document.createElement('small');
            hintSmall.innerHTML = `<em>Подсказка: ${wordData.prompt}</em>`;
            itemDiv.appendChild(hintSmall);
        }

        const optionsDiv = document.createElement('div');
        optionsDiv.className = 'mt-2';

        const options = [
            { value: "True", text: "Верно", class: "btn-success" },
            { value: "False", text: "Неверно", class: "btn-danger" },
            { value: "Not_Stated", text: "Не указано", class: "btn-warning" }
        ];

        const optionsContainer = document.createElement('div');
        optionsContainer.className = 'btn-group-vertical d-grid gap-2';
        optionsContainer.setAttribute('role', 'group');
        optionsContainer.setAttribute('aria-label', 'Варианты ответов');

        options.forEach(option => {
            const optionButton = document.createElement('button');
            optionButton.type = 'button';
            optionButton.className = `btn btn-outline-secondary option-btn`;
            optionButton.dataset.value = option.value;
            optionButton.dataset.wordId = wordData.id;
            optionButton.textContent = option.text;
            
            // Скрытый input для отправки формы
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'radio';
            hiddenInput.name = `answer_${wordData.id}`;
            hiddenInput.value = option.value;
            hiddenInput.style.display = 'none';
            hiddenInput.required = true;
            
            optionButton.addEventListener('click', function() {
                // Убираем выделение с других кнопок
                optionsContainer.querySelectorAll('.option-btn').forEach(btn => {
                    btn.classList.remove('active');
                    btn.classList.add('btn-outline-secondary');
                    btn.classList.remove('btn-success', 'btn-danger', 'btn-warning');
                });
                
                // Выделяем выбранную кнопку
                this.classList.add('active');
                this.classList.remove('btn-outline-secondary');
                this.classList.add(option.class);
                
                // Отмечаем соответствующий radio input
                hiddenInput.checked = true;
                
                // Снимаем отметку с других radio inputs
                optionsContainer.querySelectorAll('input[type="radio"]').forEach(input => {
                    if (input !== hiddenInput) {
                        input.checked = false;
                    }
                });
            });
            
            optionsContainer.appendChild(optionButton);
            optionsContainer.appendChild(hiddenInput);
        });

        optionsDiv.appendChild(optionsContainer);

        itemDiv.appendChild(optionsDiv);
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
                const questionNames = new Set();
                wordsContainer.querySelectorAll('input[type="radio"][name^="answer_"]').forEach(radio => {
                    questionNames.add(radio.name);
                });
                if (questionNames.size > 0) {
                    for (const name of questionNames) {
                        if (!document.querySelector(`input[name="${name}"]:checked`)) {
                            allAnswered = false;
                            break;
                        }
                    }
                } else if (wordsContainer.querySelector('.question-item')) {
                    // If items rendered but no names found (edge case), assume not answered.
                    allAnswered = false;
                }
            }

            if (!allAnswered && wordsContainer.querySelector('.question-item')) {
                if (!confirm('Вы не ответили на все вопросы. Вы уверены, что хотите завершить тест?')) {
                    event.preventDefault();
                    return;
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
