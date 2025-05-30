document.addEventListener('DOMContentLoaded', function() {
    const testForm = document.getElementById('dictationTestForm');
    if (!testForm) {
        console.error("Dictation test form not found!");
        return;
    }

    // Read data attributes from the form
    const timeLimitSeconds = parseInt(testForm.dataset.timeLimitSeconds || '0', 10);
    let remainingTimeSeconds = parseInt(testForm.dataset.remainingTimeSeconds || '-1', 10);
    const isTeacherPreview = testForm.dataset.isTeacherPreview === 'true';
    // const testDbId = testForm.dataset.testDbId; // Not directly used by this JS, but available

    document.querySelectorAll('.dictation-word-container').forEach(wordContainer => {
        const charInputWrapper = wordContainer.querySelector('.char-inputs-wrapper');
        if (charInputWrapper) {
            charInputWrapper.querySelectorAll('.dictation-char-input').forEach(input => {
                input.addEventListener('input', handleDictationInput);
                input.addEventListener('keydown', handleKeyDown);
            });
            // Check if initial inputs are all filled (e.g. on page reload with cached values)
            // Use a slight delay to ensure browser autofill has a chance to run.
            setTimeout(() => {
                 checkAndAddNewInput(wordContainer, wordContainer.dataset.wordId, charInputWrapper);
            }, 100);
        }
    });

    function handleDictationInput(event) {
        const currentInput = event.target;
        const wordContainer = currentInput.closest('.dictation-word-container');
        const charInputWrapper = wordContainer.querySelector('.char-inputs-wrapper');
        const wordId = wordContainer.dataset.wordId;

        if (currentInput.value.length >= 1) {
            const charIndex = parseInt(currentInput.dataset.charIndex);
            const nextCharIndex = charIndex + 1;
            let nextInput = charInputWrapper.querySelector(`.dictation-char-input[data-char-index="${nextCharIndex}"]`);

            if (nextInput) {
                nextInput.focus();
                nextInput.select();
            } else {
                // No next input, check if all are filled to add a new one
                 checkAndAddNewInput(wordContainer, wordId, charInputWrapper, true); // force focus on new if added
            }
        }
         // Always check, even if current input was cleared, to see if a new box is needed (e.g., if it was the only empty one)
        checkAndAddNewInput(wordContainer, wordId, charInputWrapper);
    }

    function checkAndAddNewInput(wordContainer, wordId, charInputWrapper, focusNew = false) {
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
            const newIndex = allInputsForWord.length; // Next index
            addNewInputBox(wordContainer, wordId, newIndex, charInputWrapper, focusNew);
        }
    }

    function addNewInputBox(wordContainer, wordId, newIndex, charInputWrapper, shouldFocus = true) {
        const newInput = document.createElement('input');
        newInput.type = 'text';
        newInput.name = `dictation_answer_${wordId}_${newIndex}`;
        newInput.className = 'dictation-char-input';
        newInput.maxLength = 1;
        newInput.dataset.wordId = wordId;
        newInput.dataset.charIndex = newIndex;
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
        const charIndex = parseInt(currentInput.dataset.charIndex);
        const charInputWrapper = currentInput.closest('.char-inputs-wrapper');

        if (event.key === 'Backspace' && currentInput.value === '') {
            if (charIndex > 0) {
                const prevCharIndex = charIndex - 1;
                const prevInput = charInputWrapper.querySelector(`.dictation-char-input[data-char-index="${prevCharIndex}"]`);
                if (prevInput) {
                    prevInput.focus();
                    prevInput.select();
                    event.preventDefault();
                }
            }
        } else if (event.key === 'ArrowLeft') {
            if (charIndex > 0) {
                const prevCharIndex = charIndex - 1;
                const prevInput = charInputWrapper.querySelector(`.dictation-char-input[data-char-index="${prevCharIndex}"]`);
                if (prevInput) {
                    prevInput.focus();
                    prevInput.select();
                    event.preventDefault();
                }
            } else {
                 event.preventDefault();
            }
        } else if (event.key === 'ArrowRight') {
            const nextCharIndex = charIndex + 1;
            const nextInput = charInputWrapper.querySelector(`.dictation-char-input[data-char-index="${nextCharIndex}"]`);
            if (nextInput) {
                nextInput.focus();
                nextInput.select();
                event.preventDefault();
            } else {
                // If at the last input, automatically try to add a new one and focus it
                const wordContainer = currentInput.closest('.dictation-word-container');
                const wordId = wordContainer.dataset.wordId;
                checkAndAddNewInput(wordContainer, wordId, charInputWrapper, true);
                event.preventDefault();
            }
        }
    }

    // Timer logic
    const timeLeftSpan = document.getElementById('time-left');
    const timerDiv = document.getElementById('timer');
    let testSubmittedByTimer = false;

    if (timeLeftSpan && timerDiv && timeLimitSeconds > 0 && !isTeacherPreview) {
        let currentRemainingTime = remainingTimeSeconds; // Use the value passed from server

        if (currentRemainingTime <= 0) { // Time was already up when page loaded
            timeLeftSpan.textContent = "00:00";
            timerDiv.innerHTML = "<strong>Время вышло!</strong> Тест будет отправлен автоматически.";
            timerDiv.classList.add('almost-up');
            if (testForm && !testForm.submitted) { // Check form.submitted
                testForm.submitted = true; // Mark as submitted
                testSubmittedByTimer = true;
                testForm.submit();
            }
        } else {
            const interval = setInterval(() => {
                if (testSubmittedByTimer || (testForm && testForm.submitted)) { // Check form.submitted
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
                    if (testForm && !testForm.submitted) { // Check form.submitted
                         testForm.submitted = true; // Mark as submitted
                         testSubmittedByTimer = true;
                         testForm.submit();
                    }
                }
            }, 1000);
        }
    } else if (timerDiv && !isTeacherPreview) { // No time limit for student
        timerDiv.textContent = "Время: Без ограничений";
        timerDiv.classList.remove('timer'); // Remove red styling if no limit
        timerDiv.style.color = 'var(--text)';
        timerDiv.style.backgroundColor = 'rgba(var(--primary-rgb), 0.05)';
        timerDiv.style.borderColor = 'rgba(var(--primary-rgb), 0.2)';
    } else if (timerDiv && isTeacherPreview) { // No timer for teacher preview
         timerDiv.style.display = 'none';
    }

    if (testForm) {
        testForm.addEventListener('submit', function() {
            if (testForm.submitted) { // Prevent re-submission
                event.preventDefault();
                return;
            }
            testForm.submitted = true; // Mark as submitted
            const submitButton = testForm.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Отправка...';
            }
            testSubmittedByTimer = true; // Also set this to stop any running timers
        });

        testForm.addEventListener('keydown', function(event) {
            if (event.key === 'Enter' && event.target.type === 'text' && event.target.classList.contains('dictation-char-input')) {
                event.preventDefault();
                const currentInput = event.target;
                const wordId = currentInput.dataset.wordId;
                const wordContainer = currentInput.closest('.dictation-word-container');
                const charInputWrapper = wordContainer.querySelector('.char-inputs-wrapper');

                const charIndex = parseInt(currentInput.dataset.charIndex);
                const nextCharIndex = charIndex + 1;
                let nextInput = charInputWrapper.querySelector(`.dictation-char-input[data-char-index="${nextCharIndex}"]`);

                if (nextInput) {
                    nextInput.focus();
                } else {
                    checkAndAddNewInput(wordContainer, wordId, charInputWrapper, true); // Pass true to focus new input
                }
            }
        });
    }
});
