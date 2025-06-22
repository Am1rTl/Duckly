document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('addLetterTestForm');
    if (!form) {
        console.error("addLetterTestForm not found!");
        return;
    }

    const testDbId = form.dataset.testDbId;
    const storageKey = form.dataset.storageKey;

    const wordsContainer = document.getElementById('test-questions-container');
    const loadingMessage = wordsContainer ? wordsContainer.querySelector('.loading-message') : null;
    const noWordsMessageContainer = document.getElementById('no-words-message-container');
    const navPanel = document.getElementById('navigation-panel-placeholder');

    const nextButton = document.getElementById('nextWordBtn');
    const prevButton = document.getElementById('prevWordBtn');
    const submitButton = document.getElementById('submitTestBtn');

    const timerDisplay = document.getElementById('timer');

    if (!wordsContainer || !loadingMessage || !noWordsMessageContainer || !navPanel || !nextButton || !prevButton || !submitButton || !timerDisplay) {
        console.error("One or more critical UI elements for add_letter test are missing.");
        if (wordsContainer) wordsContainer.innerHTML = "<p>Ошибка загрузки: критические элементы страницы отсутствуют.</p>";
        else if (form) form.innerHTML = "<p>Ошибка загрузки: критические элементы страницы отсутствуют.</p>"
        return;
    }

    let testWords = [];
    let currentWordIndex = 0;
    let formSubmittedByTimerOrCode = false;

    function hideAllControls() {
        if(nextButton) nextButton.style.display = 'none';
        if(prevButton) prevButton.style.display = 'none';
        if(submitButton) submitButton.style.display = 'none';
        if(navPanel) navPanel.style.display = 'none';
    }

    console.log("Anti-cheat check status:", window.antiCheatInitialCheckPassed);
    console.log("Test DB ID:", testDbId);
    console.log("Storage Key:", storageKey);
    
    if (window.antiCheatInitialCheckPassed === true) {
        console.log("Anti-cheat passed, loading words...");
        loadAddLetterWords();
    } else {
        console.warn("Anti-cheat initial check did not pass for add_letter test. Test data will not be loaded.");
        console.warn("Current anti-cheat status:", window.antiCheatInitialCheckPassed);
        if (loadingMessage) loadingMessage.style.display = 'none';
        const acWarningOverlay = document.querySelector('div[style*="z-index: 2147483647"]');
        if (!acWarningOverlay) {
             wordsContainer.innerHTML = '<p style="text-align:center; color: var(--danger); padding: 20px; font-size: 1.1em;">Проверка безопасности не пройдена. Загрузка теста отменена.</p>';
        }
        hideAllControls();
        // Consider adding a "back to tests" link here if appropriate
    }

    // --- 1. Load and Render Test Data ---
    async function loadAddLetterWords() {
        if (!testDbId) {
            console.error("Test DB ID is missing from form data.");
            wordsContainer.innerHTML = '<p style="text-align:center; color: var(--danger);">Ошибка конфигурации: ID теста отсутствует.</p>';
            if(loadingMessage) loadingMessage.style.display = 'none';
            hideAllControls();
            return;
        }

        try {
            const response = await fetch(`/api/test/${testDbId}/add_letter_words`);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(`Network response was not ok: ${response.status} ${response.statusText}. ${errorData.error || ''}`);
            }
            const data = await response.json();

            if (loadingMessage) loadingMessage.style.display = 'none';
            wordsContainer.innerHTML = '';
            if (navPanel) navPanel.innerHTML = '';

            if (data.words && data.words.length > 0) {
                testWords = data.words;
                testWords.forEach((wordData, index) => {
                    renderAddLetterWord(wordData, index);
                    renderNavItem(wordData, index);
                });

                await loadProgressFromServer();
                showWord(0);
                testWords.forEach((_, idx) => updateNavCompletedStatus(idx));

                if(nextButton) nextButton.addEventListener('click', handleNextButtonClick);
                if(prevButton) prevButton.addEventListener('click', handlePrevButtonClick);
                document.addEventListener('keydown', handleGlobalArrowKeys);
                initializeTimer(); // Initialize timer after words are loaded
                initializeFormSubmitListener(); // Initialize form submit listener

            } else {
                noWordsMessageContainer.innerHTML = '<p style="text-align:center; color: var(--secondary);">В этом тесте нет слов для отображения.</p>';
                hideAllControls();
                 const backLink = document.createElement('a');
                backLink.href = "/tests";
                backLink.className = "btn btn-secondary mt-3";
                backLink.textContent = "Вернуться к списку тестов";
                noWordsMessageContainer.appendChild(backLink);
            }
        } catch (error) {
            console.error("Failed to load or render add_letter test words:", error);
            if (loadingMessage) loadingMessage.style.display = 'none';
            wordsContainer.innerHTML = `<p style="text-align:center; color: var(--danger);">Ошибка загрузки вопросов: ${error.message}. Попробуйте обновить страницу.</p>`;
            hideAllControls();
            const backLinkOnError = document.createElement('a');
            backLinkOnError.href = "/tests";
            backLinkOnError.className = "btn btn-secondary mt-3";
            backLinkOnError.textContent = "Вернуться к списку тестов";
            wordsContainer.appendChild(backLinkOnError);
        }
    }

    function renderAddLetterWord(wordData, index) {
        const wordItemContainer = document.createElement('div');
        wordItemContainer.className = 'word-container mb-4';
        wordItemContainer.dataset.wordId = wordData.id;
        wordItemContainer.dataset.wordIndex = index;
        wordItemContainer.style.display = 'none';

        const header = document.createElement('p');
        header.className = 'question-header';
        header.textContent = `Вопрос ${index + 1} из ${testWords.length}`;
        wordItemContainer.appendChild(header);

        const promptP = document.createElement('p');
        promptP.className = 'prompt-translation';
        promptP.textContent = `Перевод: ${wordData.prompt}`;
        wordItemContainer.appendChild(promptP);

        const wordDisplayDiv = document.createElement('div');
        wordDisplayDiv.className = 'word-display';

        let gappedWordHtml = wordData.word_gapped;
        let inputGlobalIndex = 0; // To ensure unique names if multiple words had same input count

        for (let i = 0; i < gappedWordHtml.length; i++) {
            if (gappedWordHtml[i] === '_') {
                const input = document.createElement('input');
                input.type = 'text';
                input.className = 'letter-input';
                input.maxLength = 1;
                input.name = `answer_${wordData.id}_${inputGlobalIndex}`;
                input.dataset.wordIndex = String(index);
                input.dataset.inputIdxInWord = String(inputGlobalIndex);
                input.autocomplete = 'off';

                input.addEventListener('input', handleInputLetter);
                input.addEventListener('keydown', handleKeyDownLetter);
                wordDisplayDiv.appendChild(input);
                inputGlobalIndex++;
            } else {
                const charSpan = document.createElement('span');
                charSpan.className = 'word-char';
                charSpan.textContent = gappedWordHtml[i];
                wordDisplayDiv.appendChild(charSpan);
            }
        }
        wordItemContainer.appendChild(wordDisplayDiv);
        wordsContainer.appendChild(wordItemContainer);
    }

    function renderNavItem(wordData, index) {
        const navItem = document.createElement('div');
        navItem.className = 'nav-item';
        navItem.dataset.wordIndex = String(index);
        navItem.textContent = index + 1;
        navItem.addEventListener('click', function() {
            const targetIndex = parseInt(this.dataset.wordIndex, 10);
            if (targetIndex === currentWordIndex) return;
            const previousActiveIndex = currentWordIndex;
            currentWordIndex = targetIndex;
            showWord(currentWordIndex, previousActiveIndex);
        });
        if (navPanel) navPanel.appendChild(navItem);
    }

    function showWord(index, previousIndex = -1) {
        if (index < 0 || index >= testWords.length) return;
        if (previousIndex !== -1 && previousIndex !== index) {
            updateNavCompletedStatus(previousIndex);
        }
        currentWordIndex = index;

        const allWordItems = wordsContainer.querySelectorAll('.word-container');
        allWordItems.forEach((container, i) => {
            container.style.display = (i === index) ? 'block' : 'none';
        });

        const allNavItems = navPanel ? navPanel.querySelectorAll('.nav-item') : [];
        allNavItems.forEach((item, i) => {
            item.classList.toggle('current', i === index);
        });
        updateNavCompletedStatus(index);

        if(prevButton) prevButton.style.display = (index === 0) ? 'none' : 'inline-block';
        if(nextButton) nextButton.style.display = (index === testWords.length - 1 || testWords.length === 0) ? 'none' : 'inline-block';
        if(submitButton) submitButton.style.display = (index === testWords.length - 1 && testWords.length > 0) ? 'inline-block' : 'none';

        if (allWordItems[index]) {
            const firstInput = allWordItems[index].querySelector('.letter-input');
            if (firstInput) {
                firstInput.focus();
            }
        }
    }

    function handleNextButtonClick() {
        if (currentWordIndex < testWords.length - 1) {
            const previousIndex = currentWordIndex;
            currentWordIndex++;
            showWord(currentWordIndex, previousIndex);
        }
    }

    function handlePrevButtonClick() {
        if (currentWordIndex > 0) {
            const previousIndex = currentWordIndex;
            currentWordIndex--;
            showWord(currentWordIndex, previousIndex);
        }
    }

    function handleGlobalArrowKeys(e) {
        if (document.activeElement && document.activeElement.classList.contains('letter-input')) {
            return;
        }
        if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
            e.preventDefault();
            if (nextButton && nextButton.style.display !== 'none') nextButton.click();
        } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
            e.preventDefault();
            if (prevButton && prevButton.style.display !== 'none') prevButton.click();
        }
    }

    function handleInputLetter() {
        saveProgressToLocalStorage();
        updateNavCompletedStatus(currentWordIndex);

        if (this.value.length >= this.maxLength) {
            const parentWordDisplay = this.closest('.word-display');
            const inputsInWord = Array.from(parentWordDisplay.querySelectorAll('.letter-input'));
            const currentInputIndexInWord = inputsInWord.indexOf(this);
            if (currentInputIndexInWord < inputsInWord.length - 1) {
                inputsInWord[currentInputIndexInWord + 1].focus();
            } else {
                // если это был последний инпут слова, переходим к первому инпуту следующего слова
                const allWordContainers = Array.from(document.querySelectorAll('.word-container'));
                const currentWordContainer = this.closest('.word-container');
                const wordIdx = allWordContainers.indexOf(currentWordContainer);
                if (wordIdx < allWordContainers.length - 1) {
                    const nextWordContainer = allWordContainers[wordIdx + 1];
                    const nextInputs = Array.from(nextWordContainer.querySelectorAll('.letter-input'));
                    const previousIndex = wordIdx;
                    currentWordIndex = wordIdx + 1;
                    showWord(currentWordIndex, previousIndex);
                    if (nextInputs.length > 0) {
                        nextInputs[0].focus();
                    } else if (nextButton && nextButton.style.display !== 'none') {
                        nextButton.click();
                    }
                } else if (nextButton && nextButton.style.display !== 'none') {
                    nextButton.click();
                }
            }
        }
    }

    function handleKeyDownLetter(e) {
        const currentInput = e.target;
        const parentWordDisplay = currentInput.closest('.word-display');
        if (!parentWordDisplay) return;

        const inputsInWord = Array.from(parentWordDisplay.querySelectorAll('.letter-input'));
        const currentIndexInWord = inputsInWord.indexOf(currentInput);

        if (e.key === 'ArrowRight') {
            e.preventDefault();
            if (currentIndexInWord < inputsInWord.length - 1) {
                inputsInWord[currentIndexInWord + 1].focus();
            } else {
                const allWordContainers = Array.from(document.querySelectorAll('.word-container'));
                const currentWordContainer = currentInput.closest('.word-container');
                const currentWordGlobalIndex = allWordContainers.indexOf(currentWordContainer);
                if (currentWordGlobalIndex < allWordContainers.length - 1) {
                    showWord(currentWordGlobalIndex + 1, currentWordGlobalIndex);
                    const nextWordContainer = allWordContainers[currentWordGlobalIndex + 1];
                    const nextInputs = Array.from(nextWordContainer.querySelectorAll('.letter-input'));
                    if (nextInputs.length > 0) {
                        nextInputs[0].focus();
                    }
                }
            }
        } else if (e.key === 'ArrowLeft') {
            e.preventDefault();
            if (currentIndexInWord > 0) {
                inputsInWord[currentIndexInWord - 1].focus();
            } else {
                const allWordContainers = Array.from(document.querySelectorAll('.word-container'));
                const currentWordContainer = currentInput.closest('.word-container');
                const currentWordGlobalIndex = allWordContainers.indexOf(currentWordContainer);
                if (currentWordGlobalIndex > 0) {
                    showWord(currentWordGlobalIndex - 1, currentWordGlobalIndex);
                    const prevWordContainer = allWordContainers[currentWordGlobalIndex - 1];
                    const prevInputs = Array.from(prevWordContainer.querySelectorAll('.letter-input'));
                    if (prevInputs.length > 0) {
                        prevInputs[prevInputs.length - 1].focus();
                    }
                }
            }
        } else if (e.key === 'Backspace') {
            e.preventDefault();
            const wasEmpty = currentInput.value.length === 0;

            if (!wasEmpty) {
                currentInput.value = '';
                currentInput.dispatchEvent(new Event('input', { bubbles: true })); // Trigger autosave
            }

            if (currentIndexInWord > 0) {
                inputsInWord[currentIndexInWord - 1].focus();
            } else {
                const allWordContainers = Array.from(document.querySelectorAll('.word-container'));
                const currentWordContainer = currentInput.closest('.word-container');
                const currentWordGlobalIndex = allWordContainers.indexOf(currentWordContainer);
                if (currentWordGlobalIndex > 0) {
                    showWord(currentWordGlobalIndex - 1, currentWordGlobalIndex);
                    const prevWordContainer = allWordContainers[currentWordGlobalIndex - 1];
                    const prevInputs = Array.from(prevWordContainer.querySelectorAll('.letter-input'));
                    if (prevInputs.length > 0) {
                        prevInputs[prevInputs.length - 1].focus();
                    }
                }
            }
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (submitButton && submitButton.style.display !== 'none') {
                form.requestSubmit();
            } else if (nextButton && nextButton.style.display !== 'none') {
                nextButton.click();
            }
        }
    }

    function saveProgressToLocalStorage() {
        if (!storageKey || !testWords.length) return;
        const progress = {};
        wordsContainer.querySelectorAll('.word-container').forEach((wc) => {
            const wordIdx = parseInt(wc.dataset.wordIndex, 10); // Get the current word's index
            if(isNaN(wordIdx) || wordIdx >= testWords.length) return;

            const wordId = testWords[wordIdx].id;
            wc.querySelectorAll('.letter-input').forEach(input => {
                if(input.name) progress[input.name] = input.value;
            });
        });
        localStorage.setItem(storageKey, JSON.stringify(progress));
    }

    async function loadProgressFromServer() {
        if (!testDbId || !testWords.length) return;
        
        const isTeacherPreview = form.dataset.isTeacherPreview === 'true';
        if (isTeacherPreview) return; // Учителя не загружают прогресс
        
        try {
            const response = await fetch(`/api/test/${testDbId}/load_progress`);
            if (response.ok) {
                const data = await response.json();
                const progress = data.progress || {};
                
                console.log('Загружен сохраненный прогресс для add_letter:', progress);
                
                // Восстанавливаем ответы для каждого слова
                testWords.forEach(wordData => {
                    const savedAnswer = progress[String(wordData.id)] || '';
                    if (savedAnswer) {
                        // Находим все поля ввода для этого слова
                        const wordContainer = wordsContainer.querySelector(`.word-container[data-word-id="${wordData.id}"]`);
                        if (wordContainer) {
                            const inputs = wordContainer.querySelectorAll('.letter-input');
                            // Заполняем поля по порядку
                            for (let i = 0; i < Math.min(savedAnswer.length, inputs.length); i++) {
                                inputs[i].value = savedAnswer[i];
                            }
                        }
                    }
                });
                
                // Настраиваем автосохранение
                setupAutoSaveForAddLetter();
            }
        } catch (error) {
            console.warn('Не удалось загрузить сохраненный прогресс для add_letter:', error);
        }
    }
    
    function loadProgressFromLocalStorage() {
        // Оставляем для совместимости, но больше не используем
        console.log('loadProgressFromLocalStorage вызвана, но теперь используется серверное сохранение');
    }

    function updateNavCompletedStatus(wordIndex) {
        if (wordIndex < 0 || wordIndex >= testWords.length || !navPanel) return;
        const wordContainer = wordsContainer.querySelector(`.word-container[data-word-index="${wordIndex}"]`);
        const navItemElements = navPanel.querySelectorAll('.nav-item');
        const navItem = navItemElements[wordIndex]; // Access by index

        if (!wordContainer || !navItem) return;

        const inputs = wordContainer.querySelectorAll('.letter-input');
        let attempted = false;
        if (inputs.length > 0) {
            inputs.forEach(input => {
                if (input.value.trim() !== '') {
                    attempted = true;
                }
            });
        }
        navItem.classList.toggle('completed', attempted);
    }

    function initializeTimer() {
        const initialTimeLimitMinutes = parseFloat(timerDisplay.dataset.timeLimit || '0');
        let serverRemainingSeconds = parseInt(timerDisplay.dataset.remainingTimeSeconds || '-1', 10);
        const isTeacherPreview = form.dataset.isTeacherPreview === 'true';
        
        console.log("Timer initialization:");
        console.log("- Time limit (minutes):", initialTimeLimitMinutes);
        console.log("- Remaining seconds:", serverRemainingSeconds);
        console.log("- Is teacher preview:", isTeacherPreview);

        if (timerDisplay && !isNaN(initialTimeLimitMinutes) && initialTimeLimitMinutes > 0 && !isTeacherPreview) {
            let timeLeft;
            if (!isNaN(serverRemainingSeconds) && serverRemainingSeconds >= 0) {
                timeLeft = serverRemainingSeconds;
            } else {
                timeLeft = initialTimeLimitMinutes * 60;
            }

            if (timeLeft === 0 && serverRemainingSeconds === 0) {
                timerDisplay.textContent = "Время вышло!";
                if(!form.submitted && !formSubmittedByTimerOrCode) { formSubmittedByTimerOrCode = true; form.submit(); }
                return;
            }
            const updateTimerDisplay = () => {
                const minutes = Math.floor(timeLeft / 60);
                let seconds = timeLeft % 60;
                seconds = seconds < 10 ? '0' + seconds : seconds;
                timerDisplay.textContent = `Время: ${minutes}:${seconds}`;
            };
            updateTimerDisplay();

            const timerInterval = setInterval(() => {
                if(formSubmittedByTimerOrCode) { clearInterval(timerInterval); return; }
                timeLeft--;
                updateTimerDisplay();
                if (timeLeft <= 0) {
                    clearInterval(timerInterval);
                    timerDisplay.textContent = "Время вышло!";
                    if (!form.submitted && !formSubmittedByTimerOrCode) {
                         formSubmittedByTimerOrCode = true;
                         form.submit();
                    }
                }
            }, 1000);
        } else if (timerDisplay && !isTeacherPreview) {
            timerDisplay.textContent = "Время: Без ограничений";
        } else if (timerDisplay && isTeacherPreview) {
            timerDisplay.style.display = 'none';
        }
    }

    function initializeFormSubmitListener(){
        form.addEventListener('submit', function(e) {
            if (form.submitted) {
                e.preventDefault();
                return;
            }
            form.submitted = true;
            formSubmittedByTimerOrCode = true;
            if (storageKey) localStorage.removeItem(storageKey);

            if(submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Отправка...';
            }
            if(nextButton) nextButton.disabled = true;
            if(prevButton) prevButton.disabled = true;
        });
    }

    // Функции автосохранения для add_letter теста
    let autoSaveTimeoutAddLetter = null;
    let isAutoSaveEnabledAddLetter = false;

    function setupAutoSaveForAddLetter() {
        isAutoSaveEnabledAddLetter = true;
        console.log('Автосохранение настроено для add_letter теста:', testDbId);
        
        // Сохраняем при каждом изменении с небольшой задержкой
        document.addEventListener('input', function(event) {
            if (event.target.classList.contains('letter-input') && isAutoSaveEnabledAddLetter) {
                debouncedAutoSaveAddLetter();
            }
        });
        
        // Сохраняем при потере фокуса
        document.addEventListener('blur', function(event) {
            if (event.target.classList.contains('letter-input') && isAutoSaveEnabledAddLetter) {
                saveProgressAddLetter();
            }
        }, true);
        
        // Сохраняем перед закрытием страницы
        window.addEventListener('beforeunload', function() {
            if (isAutoSaveEnabledAddLetter) {
                saveProgressSyncAddLetter();
            }
        });
        
        // Периодическое сохранение каждые 30 секунд
        setInterval(() => {
            if (isAutoSaveEnabledAddLetter) {
                saveProgressAddLetter();
            }
        }, 30000);
    }

    function debouncedAutoSaveAddLetter() {
        if (autoSaveTimeoutAddLetter) {
            clearTimeout(autoSaveTimeoutAddLetter);
        }
        
        autoSaveTimeoutAddLetter = setTimeout(() => {
            saveProgressAddLetter();
        }, 1000);
    }

    async function saveProgressAddLetter() {
        if (!isAutoSaveEnabledAddLetter || !testDbId) return;
        
        try {
            const answers = collectCurrentAnswersAddLetter();
            if (answers.length === 0) return;
            
            const response = await fetch(`/api/test/${testDbId}/save_progress`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    answers: answers
                })
            });
            
            if (response.ok) {
                console.log('Прогресс add_letter сохранен автоматически');
            } else {
                console.warn('Не удалось сохранить прогресс add_letter:', response.status);
            }
        } catch (error) {
            console.warn('Ошибка автосохранения add_letter:', error);
        }
    }

    function saveProgressSyncAddLetter() {
        if (!isAutoSaveEnabledAddLetter || !testDbId) return;
        
        try {
            const answers = collectCurrentAnswersAddLetter();
            if (answers.length === 0) return;
            
            const xhr = new XMLHttpRequest();
            xhr.open('POST', `/api/test/${testDbId}/save_progress`, false);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.send(JSON.stringify({
                answers: answers
            }));
        } catch (error) {
            console.warn('Ошибка синхронного сохранения add_letter:', error);
        }
    }

    function collectCurrentAnswersAddLetter() {
        const answers = [];
        
        testWords.forEach(wordData => {
            const wordContainer = wordsContainer.querySelector(`.word-container[data-word-id="${wordData.id}"]`);
            if (wordContainer) {
                const inputs = wordContainer.querySelectorAll('.letter-input');
                let userAnswer = '';
                inputs.forEach(input => {
                    if (input.value) {
                        userAnswer += input.value;
                    }
                });
                
                answers.push({
                    test_word_id: wordData.id,
                    user_answer: userAnswer
                });
            }
        });
        
        return answers;
    }
});
