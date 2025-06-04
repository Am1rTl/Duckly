document.addEventListener('DOMContentLoaded', function() {
    const testForm = document.getElementById('dictationTestForm');
    if (!testForm) {
        console.error("Dictation test form not found!");
        return;
    }

    const testDbId = testForm.dataset.testDbId;
    const isTeacherPreview = testForm.dataset.isTeacherPreview === 'true';

    const wordsContainer = document.getElementById('dictation-words-container');
    const loadingMessage = document.getElementById('dictation-loading-message');
    const submitButtonArea = document.getElementById('submit-button-area');
    const submitButton = document.getElementById('submit-test-button');
    const backToTestsLink = document.getElementById('back-to-tests-link');

    if (!wordsContainer || !loadingMessage || !submitButtonArea || !submitButton || !backToTestsLink) {
        console.error("One or more required page elements for dictation test are missing.");
        if(wordsContainer) wordsContainer.innerHTML = '<p style="text-align:center; color: var(--danger);">Ошибка конфигурации страницы.</p>';
        return;
    }

    // Check anti-cheat flag
    if (window.antiCheatInitialCheckPassed === true) {
        loadDictationWords(testDbId, wordsContainer, loadingMessage, submitButtonArea, submitButton, backToTestsLink, isTeacherPreview);
    } else {
        console.warn("Anti-cheat initial check did not pass for dictation test. Test data will not be loaded.");
        if (loadingMessage) loadingMessage.style.display = 'none';
        // Check if the main anti-cheat warning is already visible
        const acWarningOverlay = document.querySelector('div[style*="z-index: 2147483647"]');
        if (!acWarningOverlay) { // Only show this if the main one isn't up
            wordsContainer.innerHTML = '<p style="text-align:center; color: var(--danger); padding: 20px; font-size: 1.1em;">Проверка безопасности не пройдена. Загрузка теста отменена.</p>';
        }
        if (submitButton) submitButton.style.display = 'none';
        if (backToTestsLink) backToTestsLink.style.display = 'inline-flex'; // Show back link
    }

    // Timer logic (from original script, largely independent of word loading)
    const timeLimitSeconds = parseInt(testForm.dataset.timeLimitSeconds || '0', 10);
    let remainingTimeSeconds = parseInt(testForm.dataset.remainingTimeSeconds || '-1', 10);
    const timeLeftSpan = document.getElementById('time-left');
    const timerDiv = document.getElementById('timer');
    let testSubmittedByTimer = false;

    if (timeLeftSpan && timerDiv && timeLimitSeconds > 0 && !isTeacherPreview) {
        let currentRemainingTime = remainingTimeSeconds;

        if (currentRemainingTime <= 0 && currentRemainingTime !== -1) {
            timeLeftSpan.textContent = "00:00";
            timerDiv.innerHTML = "<strong>Время вышло!</strong> Тест будет отправлен автоматически.";
            timerDiv.classList.add('almost-up');
            if (!testForm.submitted) {
                testForm.submitted = true;
                testSubmittedByTimer = true;
                testForm.submit();
            }
        } else if (currentRemainingTime > 0) {
            const interval = setInterval(() => {
                if (testSubmittedByTimer || testForm.submitted) {
                    clearInterval(interval);
                    return;
                }
                currentRemainingTime--;
                const minutes = Math.floor(currentRemainingTime / 60);
                const seconds = currentRemainingTime % 60;
                timeLeftSpan.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

                if (currentRemainingTime <= 60 && currentRemainingTime > 10) {
                    timerDiv.classList.add('almost-up');
                } else if (currentRemainingTime <= 10 && currentRemainingTime > 0) {
                     timerDiv.classList.add('almost-up');
                     timerDiv.style.fontWeight = 'bold';
                }

                if (currentRemainingTime <= 0) {
                    clearInterval(interval);
                    timeLeftSpan.textContent = "00:00";
                    timerDiv.innerHTML = "<strong>Время вышло!</strong> Тест отправляется...";
                    if (!testForm.submitted) {
                         testForm.submitted = true;
                         testSubmittedByTimer = true;
                         testForm.submit();
                    }
                }
            }, 1000);
        }
    } else if (timerDiv && !isTeacherPreview) {
        timerDiv.textContent = "Время: Без ограничений";
        timerDiv.classList.remove('timer');
        timerDiv.style.color = 'var(--text)';
        timerDiv.style.backgroundColor = 'rgba(var(--primary-rgb), 0.05)';
        timerDiv.style.borderColor = 'rgba(var(--primary-rgb), 0.2)';
    } else if (timerDiv && isTeacherPreview) {
         timerDiv.style.display = 'none';
    }

    testForm.addEventListener('submit', function(event) {
        if (testForm.submitted) {
            event.preventDefault();
            return;
        }
        testForm.submitted = true;
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Отправка...';
        }
        testSubmittedByTimer = true;
    });

    testForm.addEventListener('keydown', function(event) {
        if (event.key === 'Enter' && event.target.type === 'text' && event.target.classList.contains('dictation-char-input')) {
            event.preventDefault();
            const currentInput = event.target;
            const wordContainer = currentInput.closest('.dictation-word-container');
            const charInputWrapper = wordContainer.querySelector('.char-inputs-wrapper');
            const wordId = wordContainer.dataset.wordId;
            const charIndex = parseInt(currentInput.dataset.charIndex, 10);
            const nextCharIndex = charIndex + 1;
            let nextInput = charInputWrapper.querySelector(`.dictation-char-input[data-char-index="${nextCharIndex}"]`);

            if (nextInput) {
                nextInput.focus();
            } else {
                if (currentInput.value.length > 0) {
                    checkAndAddNewInput(wordContainer, wordId, charInputWrapper, true);
                }
            }
        }
    });
});

async function loadDictationWords(test_db_id, wordsContainer, loadingMessage, submitButtonArea, submitButton, backToTestsLink, isTeacherPreview) {
    try {
        // Загружаем слова теста
        const response = await fetch(`/api/test/${test_db_id}/dictation_words`);
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            console.error("Error fetching dictation words:", response.status, errorData);
            throw new Error(`Ошибка сети: ${response.status} ${response.statusText}. ${errorData.error || ''}`);
        }
        const data = await response.json();

        // Загружаем сохраненный прогресс (только для студентов)
        let savedProgress = {};
        if (!isTeacherPreview) {
            try {
                const progressResponse = await fetch(`/api/test/${test_db_id}/load_progress`);
                if (progressResponse.ok) {
                    const progressData = await progressResponse.json();
                    savedProgress = progressData.progress || {};
                    console.log('Загружен сохраненный прогресс:', savedProgress);
                }
            } catch (error) {
                console.warn('Не удалось загрузить сохраненный прогресс:', error);
            }
        }

        if (loadingMessage) loadingMessage.style.display = 'none';
        wordsContainer.innerHTML = '';

        if (data.words && data.words.length > 0) {
            data.words.forEach(wordData => {
                const wordItem = document.createElement('div');
                wordItem.className = 'dictation-word-container word-item';
                wordItem.dataset.wordId = wordData.id;

                const promptPara = document.createElement('p');
                promptPara.className = 'lead';
                promptPara.textContent = wordData.prompt;
                wordItem.appendChild(promptPara);

                const charInputsWrapper = document.createElement('div');
                charInputsWrapper.className = 'char-inputs-wrapper';

                // Получаем сохраненный ответ для этого слова
                const savedAnswer = savedProgress[String(wordData.id)] || '';
                const savedChars = Array.from(savedAnswer);
                
                // Создаем минимум 3 поля ввода или столько, сколько было сохранено + 1
                const numInputs = Math.max(3, savedChars.length + 1);

                for (let i = 0; i < numInputs; i++) {
                    const input = document.createElement('input');
                    input.type = 'text';
                    input.name = `dictation_answer_${wordData.id}_${i}`;
                    input.className = 'dictation-char-input';
                    input.maxLength = 1;
                    input.dataset.wordId = String(wordData.id);
                    input.dataset.charIndex = String(i);
                    input.autocomplete = 'off';
                    input.spellcheck = false;
                    input.setAttribute('aria-label', `Character ${i + 1} for word hint ${wordData.prompt.substring(0,30)}`);

                    // Восстанавливаем сохраненное значение
                    if (i < savedChars.length) {
                        input.value = savedChars[i];
                    }

                    input.addEventListener('input', handleDictationInput);
                    input.addEventListener('keydown', handleKeyDown);
                    charInputsWrapper.appendChild(input);
                }
                wordItem.appendChild(charInputsWrapper);
                wordsContainer.appendChild(wordItem);

                setTimeout(() => {
                     checkAndAddNewInput(wordItem, String(wordData.id), charInputsWrapper);
                }, 50);
            });

            // Настраиваем автосохранение для студентов
            if (!isTeacherPreview) {
                setupAutoSave(test_db_id);
            }

            if (submitButton) submitButton.style.display = 'inline-flex';
            if (backToTestsLink) backToTestsLink.style.display = 'none';

        } else {
            wordsContainer.innerHTML = '<p style="text-align:center; color: var(--danger); padding: 20px; font-size: 1.1em;">В этом тесте нет слов для отображения.</p>';
            if (submitButton) submitButton.style.display = 'none';
            if (backToTestsLink) backToTestsLink.style.display = 'inline-flex';
        }
    } catch (error) {
        console.error("Failed to load or render dictation words:", error);
        if (loadingMessage) loadingMessage.style.display = 'none';
        wordsContainer.innerHTML = `<p style="text-align:center; color: var(--danger); padding: 20px; font-size: 1.1em;">Ошибка загрузки слов: ${error.message}. Пожалуйста, попробуйте обновить страницу.</p>`;
        if (submitButton) submitButton.style.display = 'none';
        if (backToTestsLink) backToTestsLink.style.display = 'inline-flex';
    }
}


// --- Helper functions (Retained from original script, ensure they are compatible) ---
function handleDictationInput(event) {
    const currentInput = event.target;
    const wordContainer = currentInput.closest('.dictation-word-container');
    if (!wordContainer) return;
    const charInputWrapper = wordContainer.querySelector('.char-inputs-wrapper');
    const wordId = wordContainer.dataset.wordId;

    if (currentInput.value.length >= 1) {
        const charIndex = parseInt(currentInput.dataset.charIndex, 10);
        const nextCharIndex = charIndex + 1;
        let nextInput = charInputWrapper.querySelector(`.dictation-char-input[data-char-index="${nextCharIndex}"]`);

        if (nextInput) {
            nextInput.focus();
        } else {
            checkAndAddNewInput(wordContainer, wordId, charInputWrapper, true);
        }
    }
    checkAndAddNewInput(wordContainer, wordId, charInputWrapper);
}

function checkAndAddNewInput(wordContainer, wordId, charInputWrapper, focusNew = false) {
    if (!charInputWrapper) return;
    const allInputsForWord = charInputWrapper.querySelectorAll('.dictation-char-input');
    let allCurrentlyFilled = true;

    if (allInputsForWord.length === 0) {
        allCurrentlyFilled = false;
    } else {
        for (const inp of allInputsForWord) {
            if (inp.value.length === 0) {
                allCurrentlyFilled = false;
                break;
            }
        }
    }

    if (allCurrentlyFilled) {
        const newIndex = allInputsForWord.length;
        addNewInputBox(wordContainer, wordId, newIndex, charInputWrapper, focusNew);
    }
}

function addNewInputBox(wordContainer, wordId, newIndex, charInputWrapper, shouldFocus = true) {
    const newInput = document.createElement('input');
    newInput.type = 'text';
    newInput.name = `dictation_answer_${wordId}_${newIndex}`;
    newInput.className = 'dictation-char-input';
    newInput.maxLength = 1;
    newInput.dataset.wordId = String(wordId);
    newInput.dataset.charIndex = String(newIndex);
    newInput.autocomplete = 'off';
    newInput.spellcheck = false;

    let hintText = "current word";
    const hintElement = wordContainer.querySelector('p.lead');
    if (hintElement) {
        hintText = hintElement.textContent.trim().substring(0,30);
    }
    newInput.setAttribute('aria-label', `Character ${newIndex + 1} for word hint ${hintText}`);

    newInput.addEventListener('input', handleDictationInput);
    newInput.addEventListener('keydown', handleKeyDown);

    if (charInputWrapper) {
        charInputWrapper.appendChild(newInput);
        if (shouldFocus) {
            newInput.focus();
        }
    } else {
        console.error("Error: Could not find .char-inputs-wrapper for wordId:", wordId, "when adding new input box.");
    }
}

function handleKeyDown(event) {
    const currentInput = event.target;
    const charIndex = parseInt(currentInput.dataset.charIndex, 10);
    const charInputWrapper = currentInput.closest('.char-inputs-wrapper');
    if (!charInputWrapper) return;

    if (event.key === 'Backspace' && currentInput.value === '') {
        if (charIndex > 0) {
            const prevCharIndex = charIndex - 1;
            const prevInput = charInputWrapper.querySelector(`.dictation-char-input[data-char-index="${prevCharIndex}"]`);
            if (prevInput) {
                prevInput.focus();
                event.preventDefault();
            }
        }
    } else if (event.key === 'ArrowLeft') {
        if (currentInput.selectionStart === 0 && charIndex > 0) {
            const prevCharIndex = charIndex - 1;
            const prevInput = charInputWrapper.querySelector(`.dictation-char-input[data-char-index="${prevCharIndex}"]`);
            if (prevInput) {
                prevInput.focus();
                event.preventDefault();
            }
        }
    } else if (event.key === 'ArrowRight') {
         if (currentInput.selectionStart === currentInput.value.length) {
            const nextCharIndex = charIndex + 1;
            const nextInput = charInputWrapper.querySelector(`.dictation-char-input[data-char-index="${nextCharIndex}"]`);
            if (nextInput) {
                nextInput.focus();
                event.preventDefault();
            } else {
                if (currentInput.value.length > 0) {
                    const wordContainer = currentInput.closest('.dictation-word-container');
                    const wordId = wordContainer.dataset.wordId;
                    checkAndAddNewInput(wordContainer, wordId, charInputWrapper, true);
                    event.preventDefault();
                }
            }
        }
    }
}

// Функции для автосохранения прогресса
let autoSaveTimeout = null;
let isAutoSaveEnabled = false;

function setupAutoSave(testDbId) {
    isAutoSaveEnabled = true;
    console.log('Автосохранение настроено для теста:', testDbId);
    
    // Сохраняем при каждом изменении с небольшой задержкой
    document.addEventListener('input', function(event) {
        if (event.target.classList.contains('dictation-char-input') && isAutoSaveEnabled) {
            debouncedAutoSave(testDbId);
        }
    });
    
    // Сохраняем при потере фокуса
    document.addEventListener('blur', function(event) {
        if (event.target.classList.contains('dictation-char-input') && isAutoSaveEnabled) {
            saveProgress(testDbId);
        }
    }, true);
    
    // Сохраняем перед закрытием страницы
    window.addEventListener('beforeunload', function() {
        if (isAutoSaveEnabled) {
            saveProgressSync(testDbId);
        }
    });
    
    // Периодическое сохранение каждые 30 секунд
    setInterval(() => {
        if (isAutoSaveEnabled) {
            saveProgress(testDbId);
        }
    }, 30000);
}

function debouncedAutoSave(testDbId) {
    if (autoSaveTimeout) {
        clearTimeout(autoSaveTimeout);
    }
    
    autoSaveTimeout = setTimeout(() => {
        saveProgress(testDbId);
    }, 1000); // Сохраняем через 1 секунду после последнего изменения
}

async function saveProgress(testDbId) {
    if (!isAutoSaveEnabled) return;
    
    try {
        const answers = collectCurrentAnswers();
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
            console.log('Прогресс сохранен автоматически');
        } else {
            console.warn('Не удалось сохранить прогресс:', response.status);
        }
    } catch (error) {
        console.warn('Ошибка автосохранения:', error);
    }
}

function saveProgressSync(testDbId) {
    if (!isAutoSaveEnabled) return;
    
    try {
        const answers = collectCurrentAnswers();
        if (answers.length === 0) return;
        
        // Синхронный запрос для сохранения перед закрытием страницы
        const xhr = new XMLHttpRequest();
        xhr.open('POST', `/api/test/${testDbId}/save_progress`, false);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.send(JSON.stringify({
            answers: answers
        }));
    } catch (error) {
        console.warn('Ошибка синхронного сохранения:', error);
    }
}

function collectCurrentAnswers() {
    const answers = [];
    const wordContainers = document.querySelectorAll('.dictation-word-container');
    
    wordContainers.forEach(container => {
        const wordId = container.dataset.wordId;
        const inputs = container.querySelectorAll('.dictation-char-input');
        
        let userAnswer = '';
        inputs.forEach(input => {
            if (input.value) {
                userAnswer += input.value;
            }
        });
        
        if (wordId) {
            answers.push({
                test_word_id: parseInt(wordId),
                user_answer: userAnswer
            });
        }
    });
    
    return answers;
}
