document.addEventListener('DOMContentLoaded', function() {
    const timerDisplay = document.getElementById('timer');
    const testForm = document.getElementById('trueFalseTestForm');

    if (!timerDisplay || !testForm) {
        console.error("Timer display or test form not found for True/False test!");
        if(timerDisplay) timerDisplay.textContent = "Ошибка инициализации таймера.";
        return;
    }

    const timeLimitMinutes = parseInt(timerDisplay.dataset.timeLimit || '0', 10);
    let remainingTimeSeconds = parseInt(timerDisplay.dataset.remainingTimeSeconds || '-1', 10);
    let timerInterval;

    function submitFormLogic() {
        clearInterval(timerInterval);
        timerDisplay.textContent = "Время вышло!";

        setTimeout(() => {
             if (typeof testForm.submit === 'function' && !testForm.submitted) {
                testForm.submitted = true;
                const submitButton = testForm.querySelector('button[type="submit"]');
                if (submitButton) {
                    submitButton.disabled = true;
                    submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Отправка...';
                }
                testForm.submit();
            }
        }, 1000);
    }

    if (timeLimitMinutes > 0 && remainingTimeSeconds >= 0) {
        let timeLeft = remainingTimeSeconds;
        const updateTimer = () => {
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
    } else if (timeLimitMinutes > 0 && remainingTimeSeconds === -1) {
        let timeLeft = timeLimitMinutes * 60;
        const updateTimer = () => {
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

    testForm.addEventListener('submit', function(event) {
        if (testForm.submitted) {
            event.preventDefault();
            return;
        }

        // Validation for unanswered questions
        const questionNames = new Set();
        testForm.querySelectorAll('input[type="radio"]').forEach(radio => {
            if (radio.name.startsWith('answer_')) {
                questionNames.add(radio.name);
            }
        });

        let allAnswered = true;
        for (const name of questionNames) {
            if (!document.querySelector(`input[name="${name}"]:checked`)) {
                allAnswered = false;
                break;
            }
        }

        if (!allAnswered) {
            if (!confirm('Вы не ответили на все вопросы. Вы уверены, что хотите завершить тест?')) {
                event.preventDefault(); // Stop submission
                // Re-enable submit button if user cancels
                const sb = testForm.querySelector('button[type="submit"]');
                if (sb) {
                    sb.disabled = false;
                    sb.innerHTML = '<i class="fas fa-check-circle"></i> Завершить тест';
                }
                return;
            }
        }
        // Proceed with submission
        testForm.submitted = true;
        const submitButton = testForm.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Отправка...';
        }
    });
});
