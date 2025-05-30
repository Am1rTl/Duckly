document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('addLetterTestForm');
    if (!form) return;

    const storageKey = form.dataset.storageKey;
    const wordContainers = document.querySelectorAll('.word-container');
    const navItems = document.querySelectorAll('.nav-panel .nav-item');
    const nextButton = document.getElementById('nextWordBtn');
    const prevButton = document.getElementById('prevWordBtn');
    const submitButton = document.getElementById('submitTestBtn');
    const timerDisplay = document.getElementById('timer');

    let currentWordIndex = 0;

    // Timer variables from data attributes
    const initialTimeLimitMinutes = parseFloat(timerDisplay.dataset.timeLimit || '0');
    let serverRemainingSeconds = parseInt(timerDisplay.dataset.remainingTimeSeconds || '-1', 10);


    function saveProgressToLocalStorage() {
        if (!storageKey) return;
        const progress = {};
        document.querySelectorAll('.letter-input').forEach(input => {
            progress[input.name] = input.value;
        });
        localStorage.setItem(storageKey, JSON.stringify(progress));
    }

    function loadProgressFromLocalStorage() {
        if (!storageKey) return;
        const savedProgress = localStorage.getItem(storageKey);
        if (savedProgress) {
            try {
                const progress = JSON.parse(savedProgress);
                for (const name in progress) {
                    const input = document.querySelector(`.letter-input[name="${name}"]`);
                    if (input) {
                        input.value = progress[name];
                    }
                }
            } catch (e) {
                console.error("Error loading progress from localStorage:", e);
                localStorage.removeItem(storageKey); // Clear corrupted data
            }
        }
    }

    function updateNavCompletedStatus(wordIndex) {
        const wordContainer = wordContainers[wordIndex];
        if (!wordContainer) return;
        const inputs = wordContainer.querySelectorAll('.letter-input');
        let attempted = false;
        inputs.forEach(input => {
            if (input.value.trim() !== '') {
                attempted = true;
            }
        });
        if (navItems[wordIndex]) {
            if (attempted) {
                navItems[wordIndex].classList.add('completed');
            } else {
                 navItems[wordIndex].classList.remove('completed');
            }
        }
    }

    function showWord(index, previousIndex = -1) {
        if (previousIndex !== -1 && previousIndex !== index) {
            updateNavCompletedStatus(previousIndex);
        }

        wordContainers.forEach((container, i) => {
            container.style.display = (i === index) ? 'block' : 'none';
        });
        navItems.forEach((item, i) => {
            item.classList.toggle('current', i === index);
            if (i !== index) updateNavCompletedStatus(i);
        });
        updateNavCompletedStatus(index);


        if(prevButton) prevButton.style.display = (index === 0) ? 'none' : 'inline-block';
        if(nextButton) nextButton.style.display = (index === wordContainers.length - 1) ? 'none' : 'inline-block';
        if(submitButton) submitButton.style.display = (index === wordContainers.length - 1) ? 'inline-block' : 'none';

        if (wordContainers[index]) {
            const firstInput = wordContainers[index].querySelector('.letter-input');
            if (firstInput) {
                firstInput.focus();
            }
        }
    }

    if (wordContainers.length > 0) {
        loadProgressFromLocalStorage();
        showWord(currentWordIndex);
        wordContainers.forEach((_, idx) => updateNavCompletedStatus(idx));
    } else {
        if(nextButton) nextButton.style.display = 'none';
        if(prevButton) prevButton.style.display = 'none';
        if(submitButton) submitButton.style.display = 'none';
    }

    if(nextButton) {
        nextButton.addEventListener('click', function() {
            if (currentWordIndex < wordContainers.length - 1) {
                const previousIndex = currentWordIndex;
                currentWordIndex++;
                showWord(currentWordIndex, previousIndex);
            }
        });
    }

    if(prevButton) {
        prevButton.addEventListener('click', function() {
            if (currentWordIndex > 0) {
                const previousIndex = currentWordIndex;
                currentWordIndex--;
                showWord(currentWordIndex, previousIndex);
            }
        });
    }

    navItems.forEach((item, index) => {
        item.addEventListener('click', function() {
            if (index === currentWordIndex) return;
            const previousIndex = currentWordIndex;
            currentWordIndex = index;
            showWord(currentWordIndex, previousIndex);
        });
    });

    document.querySelectorAll('.letter-input').forEach(input => {
        input.addEventListener('input', function() {
            saveProgressToLocalStorage();
            updateNavCompletedStatus(currentWordIndex);

            if (this.value.length >= this.maxLength) {
                let currentElement = this;
                let nextSibling = currentElement.nextElementSibling;
                while(nextSibling) {
                    if (nextSibling.classList.contains('letter-input')) {
                        nextSibling.focus();
                        break;
                    }
                    if (nextSibling.classList.contains('word-char')) {
                         currentElement = nextSibling;
                         nextSibling = currentElement.nextElementSibling;
                    } else {
                        break;
                    }
                }
            }
        });

        input.addEventListener('keydown', function(e) {
            const parentWordDisplay = this.closest('.word-display');
            if (!parentWordDisplay) return;
            const inputsInWord = Array.from(parentWordDisplay.querySelectorAll('.letter-input'));
            const currentIndexInWord = inputsInWord.indexOf(this);

            if (e.key === 'ArrowRight') {
                e.preventDefault();
                if (currentIndexInWord < inputsInWord.length - 1) {
                    inputsInWord[currentIndexInWord + 1].focus();
                } else if (nextButton && currentWordIndex < wordContainers.length - 1) {
                    nextButton.click();
                }
            } else if (e.key === 'ArrowLeft') {
                e.preventDefault();
                if (currentIndexInWord > 0) {
                    inputsInWord[currentIndexInWord - 1].focus();
                } else if (prevButton && currentWordIndex > 0) {
                    prevButton.click();
                }
            } else if (e.key === 'Backspace' && this.value.length === 0) {
                if (currentIndexInWord > 0) {
                    inputsInWord[currentIndexInWord - 1].focus();
                }
            }
        });
    });

    document.addEventListener('keydown', function(e) {
        if (document.activeElement && document.activeElement.classList.contains('letter-input')) {
            // If focus is on a letter input, let the input's specific keydown handlers manage.
            return;
        }
        if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
            e.preventDefault();
            if (nextButton && nextButton.style.display !== 'none') {
                nextButton.click();
            }
        } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
            e.preventDefault();
            if (prevButton && prevButton.style.display !== 'none') {
                prevButton.click();
            }
        }
    });

    if (timerDisplay && !isNaN(initialTimeLimitMinutes) && initialTimeLimitMinutes > 0) {
        let timeLeft;
        if (!isNaN(serverRemainingSeconds) && serverRemainingSeconds >= 0) {
            timeLeft = serverRemainingSeconds;
        } else {
            timeLeft = initialTimeLimitMinutes * 60;
        }

        if (timeLeft === 0 && serverRemainingSeconds === 0) { // Check if time was already up from server
            timerDisplay.textContent = "Время вышло!";
            console.log("Time is up on server load (from data attr). Submitting form.");
            if(!form.submitted) { form.submitted = true; form.submit(); }
            return; // Stop further timer setup
        }

        const updateTimerDisplay = () => {
            const minutes = Math.floor(timeLeft / 60);
            let seconds = timeLeft % 60;
            seconds = seconds < 10 ? '0' + seconds : seconds;
            timerDisplay.textContent = `Время: ${minutes}:${seconds}`;
        };

        updateTimerDisplay();

        const timerInterval = setInterval(() => {
            timeLeft--;
            updateTimerDisplay();

            if (timeLeft <= 0) {
                clearInterval(timerInterval);
                timerDisplay.textContent = "Время вышло!";
                if (!form.submitted) {
                     console.log("Client timer reached zero. Submitting form.");
                     form.submitted = true;
                     form.submit();
                }
            }
        }, 1000);
    } else if (timerDisplay) {
        timerDisplay.textContent = "Время: Без ограничений";
    }

    form.addEventListener('submit', function(e) {
        if (form.submitted) { // Prevent re-submission
            e.preventDefault();
            return;
        }
        form.submitted = true; // Mark form as submitted
        if (storageKey) {
            localStorage.removeItem(storageKey);
        }
        console.log("Form submitted by user or timer.");
        if(submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Отправка...';
        }
        if(nextButton) nextButton.disabled = true;
        if(prevButton) prevButton.disabled = true;

    });
});
