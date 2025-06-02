document.addEventListener('DOMContentLoaded', function() {
    const testForm = document.getElementById('test-form');
    if (!testForm) {
        console.error("Multiple choice test form ('test-form') not found!");
        return;
    }

    const testDbId = testForm.dataset.testDbId;

    const questionsContainer = document.getElementById('test-questions-container');
    const loadingMessage = questionsContainer ? questionsContainer.querySelector('.loading-message') : null;
    const noWordsMessageContainer = document.getElementById('no-words-message-container');

    const timerDisplay = document.getElementById('timer');
    const progressBar = document.getElementById('progress-bar');
    const prevButton = document.getElementById('prev-btn');
    const nextButton = document.getElementById('next-btn');
    const submitButton = document.getElementById('submit-btn');
    const isTeacherPreview = testForm.dataset.isTeacherPreview === 'true';


    if (!questionsContainer || !loadingMessage || !noWordsMessageContainer || !timerDisplay || !progressBar || !prevButton || !nextButton || !submitButton) {
        console.error("One or more critical elements for the multiple choice test are missing.");
        if(questionsContainer) questionsContainer.innerHTML = '<p style="text-align:center; color:var(--danger);">Ошибка загрузки теста: отсутствует критический элемент.</p>';
        hideControls();
        return;
    }

    let testWordsData = [];
    let userAnswers = [];
    let currentQuestionIndex = 0;
    let timerInterval;
    let timeLeft = 0;
    const timeLimit = parseInt(timerDisplay.dataset.timeLimit || '0', 10); // timeLimit is in minutes from HTML

    function hideControls() {
        if(prevButton) prevButton.style.display = 'none';
        if(nextButton) nextButton.style.display = 'none';
        if(submitButton) submitButton.style.display = 'none';
        if(progressBar) progressBar.style.display = 'none';
        if(timerDisplay && !isTeacherPreview) timerDisplay.textContent = "Тест не может быть загружен."; // Don't hide timer if it should show "no limit"
        else if (timerDisplay && isTeacherPreview) timerDisplay.style.display = 'none';
    }

    if (window.antiCheatInitialCheckPassed === true) {
        loadAndRenderMCQuestions();
    } else {
        console.warn("Anti-cheat initial check did not pass for multiple_choice test. Test data will not be loaded.");
        if (loadingMessage) loadingMessage.style.display = 'none';
        const acWarningOverlay = document.querySelector('div[style*="z-index: 2147483647"]');
        if (!acWarningOverlay && questionsContainer) {
             questionsContainer.innerHTML = '<p style="text-align:center; color: var(--danger); padding: 20px; font-size: 1.1em;">Проверка безопасности не пройдена. Загрузка теста отменена.</p>';
        }
        hideControls();
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


    async function loadAndRenderMCQuestions() {
        if (!testDbId) {
            loadingMessage.textContent = 'Ошибка: ID теста не найден.';
            loadingMessage.style.color = 'var(--danger)';
            hideControls();
            return;
        }
        try {
            const response = await fetch(`/api/test/${testDbId}/multiple_choice_single_words`);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(`Network error: ${response.status} ${response.statusText}. ${errorData.error || ''}`);
            }
            const data = await response.json();

            if (loadingMessage) loadingMessage.style.display = 'none';
            questionsContainer.innerHTML = '';
            if(progressBar) progressBar.innerHTML = '';

            if (data.words && data.words.length > 0) {
                testWordsData = data.words;
                userAnswers = new Array(testWordsData.length).fill(null);

                testWordsData.forEach((wordData, index) => {
                    renderMCQuestion(wordData, index);
                    renderProgressBarItem(index);
                });

                showQuestion(0);
                initializeTimerAndSubmit(); // Call after successful load

                prevButton.addEventListener('click', handlePrevButtonClick);
                nextButton.addEventListener('click', handleNextButtonClick);

            } else {
                noWordsMessageContainer.innerHTML = '<p style="text-align:center; color:var(--secondary);">В этом тесте нет вопросов.</p>';
                hideControls();
                const backLink = document.createElement('a');
                backLink.href = "/tests";
                backLink.className = "btn btn-secondary mt-3";
                backLink.textContent = "Вернуться к списку тестов";
                noWordsMessageContainer.appendChild(backLink);
                noWordsMessageContainer.style.textAlign = 'center';
            }
        } catch (error) {
            console.error("Failed to load or render multiple choice questions:", error);
            if (loadingMessage) loadingMessage.style.display = 'none';
            questionsContainer.innerHTML = `<p style="text-align:center; color:var(--danger);">Ошибка загрузки вопросов: ${error.message}</p>`;
            hideControls();
             const backLinkOnError = document.createElement('a');
            backLinkOnError.href = "/tests";
            backLinkOnError.className = "btn btn-secondary mt-3";
            backLinkOnError.textContent = "Вернуться к списку тестов";
            questionsContainer.appendChild(backLinkOnError);
        }
    }

    function renderMCQuestion(wordData, index) {
        const questionItem = document.createElement('div');
        questionItem.className = 'word-container mc-question-item';
        questionItem.dataset.index = String(index);
        questionItem.style.display = 'none';

        const questionTextDiv = document.createElement('div');
        questionTextDiv.className = 'question-text';
        questionTextDiv.textContent = wordData.question;
        questionItem.appendChild(questionTextDiv);

        if (wordData.prompt) {
            const promptDiv = document.createElement('div');
            promptDiv.className = 'prompt-text info-text mb-3';
            promptDiv.textContent = wordData.prompt;
            questionItem.appendChild(promptDiv);
        }

        const hiddenInput = document.createElement('input');
        hiddenInput.type = 'hidden';
        hiddenInput.name = `answer${wordData.id}`;
        hiddenInput.id = `answer-input-${wordData.id}`;
        questionItem.appendChild(hiddenInput); // Append to question item, form will still find it by name

        const optionsGrid = document.createElement('div');
        optionsGrid.className = 'options-grid';
        wordData.options.forEach(optionText => {
            const optionButton = document.createElement('button');
            optionButton.type = 'button';
            optionButton.className = 'option-btn';
            optionButton.dataset.wordId = String(wordData.id);
            optionButton.dataset.value = optionText;
            optionButton.textContent = optionText;

            optionButton.addEventListener('click', function() {
                userAnswers[currentQuestionIndex] = optionText;
                hiddenInput.value = optionText;

                optionsGrid.querySelectorAll('.option-btn').forEach(btn => btn.classList.remove('selected'));
                this.classList.add('selected');
                updateProgressBar();
            });
            optionsGrid.appendChild(optionButton);
        });
        questionItem.appendChild(optionsGrid);
        questionsContainer.appendChild(questionItem);
    }

    function renderProgressBarItem(index) {
        const item = document.createElement('div');
        item.className = 'progress-item';
        item.dataset.index = String(index);
        item.textContent = index + 1;
        item.addEventListener('click', function() {
            const targetIndex = parseInt(this.dataset.index, 10);
            if (userAnswers[targetIndex] !== null ||
                (targetIndex === currentQuestionIndex + 1 && userAnswers[currentQuestionIndex] !== null) ||
                targetIndex <= currentQuestionIndex) {
                showQuestion(targetIndex);
            } else {
                alert('Пожалуйста, сначала ответьте на текущий вопрос.');
            }
        });
        if(progressBar) progressBar.appendChild(item);
    }

    function showQuestion(index) {
        currentQuestionIndex = index;
        questionsContainer.querySelectorAll('.word-container').forEach((container, idx) => {
            container.style.display = (idx === index) ? 'block' : 'none';
        });

        updateProgressBar();

        if (testWordsData[currentQuestionIndex]) {
            const wordId = testWordsData[currentQuestionIndex].id;
            const selectedValue = userAnswers[currentQuestionIndex];
            const currentQuestionElement = questionsContainer.querySelector(`.word-container[data-index="${currentQuestionIndex}"]`);
            if (selectedValue && currentQuestionElement) {
                currentQuestionElement.querySelectorAll(`.option-btn[data-word-id="${wordId}"]`).forEach(btn => {
                    btn.classList.remove('selected');
                    if (btn.dataset.value === selectedValue) {
                        btn.classList.add('selected');
                    }
                });
            }
        }
    }

    function updateProgressBar() {
        if (!progressBar) return;
        progressBar.querySelectorAll('.progress-item').forEach((item, index) => {
            item.classList.remove('current', 'completed', 'answered');
            if (userAnswers[index] !== null) {
                item.classList.add('answered');
            }
            if (index === currentQuestionIndex) {
                item.classList.add('current');
            } else if (index < currentQuestionIndex && userAnswers[index] !== null) {
                 item.classList.add('completed');
            }
        });

        prevButton.style.display = (currentQuestionIndex === 0 || testWordsData.length === 0) ? 'none' : 'inline-flex';
        prevButton.disabled = currentQuestionIndex === 0;

        if (currentQuestionIndex === testWordsData.length - 1 && testWordsData.length > 0) {
            nextButton.style.display = 'none';
            submitButton.style.display = 'inline-flex';
        } else if (testWordsData.length === 0) {
            nextButton.style.display = 'none';
            submitButton.style.display = 'none';
        }
         else {
            nextButton.style.display = 'inline-flex';
            submitButton.style.display = 'none';
        }
    }

    function handlePrevButtonClick() {
        if (currentQuestionIndex > 0) {
            showQuestion(currentQuestionIndex - 1);
        }
    }

    function handleNextButtonClick() {
        if (userAnswers[currentQuestionIndex] === null && testWordsData.length > 0) { // Check if there are words
             alert('Пожалуйста, выберите ответ.');
             return;
        }
        if (currentQuestionIndex < testWordsData.length - 1) {
            showQuestion(currentQuestionIndex + 1);
        }
    }

    function initializeTimerAndSubmit() {
        // Timer functions
        function startTimer() {
            if (timeLimit > 0 && !isTeacherPreview) {
                timeLeft = timeLimit * 60;
                updateTimerDisplay();
                timerInterval = setInterval(updateTimerLogic, 1000);
            } else if (!isTeacherPreview) {
                timerDisplay.textContent = "Время: Без ограничений";
            } else { // Teacher preview
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

        function updateTimerLogic() {
            if (testForm.submitted) {
                clearInterval(timerInterval);
                return;
            }
            if (timeLeft <= 0) {
                clearInterval(timerInterval);
                if (!testForm.submitted) {
                     testForm.submitted = true;
                     alert("Время вышло! Тест будет отправлен.");
                     testForm.submit();
                }
                return;
            }
            timeLeft--;
            updateTimerDisplay();
        }

        startTimer(); // Call to start timer after words are loaded

        // Form submission
        testForm.addEventListener('submit', (e) => {
            if (testForm.submitted) {
                e.preventDefault();
                return;
            }

            const allAnswered = userAnswers.every(answer => answer !== null);
            if (!allAnswered && testWordsData.length > 0) { // Only ask confirm if there were questions
                if (!confirm('Вы не ответили на все вопросы. Вы уверены, что хотите завершить тест?')) {
                    e.preventDefault();
                    return;
                }
            }

            testForm.submitted = true;
            clearInterval(timerInterval);

            if(submitButton){
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Отправка...';
            }
            if(prevButton) prevButton.disabled = true;
            if(nextButton) nextButton.disabled = true;
        });
    }
});
