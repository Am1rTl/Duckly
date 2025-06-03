document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const wordDisplay = document.getElementById('word-display');
    const wordHint = document.getElementById('word-hint');
    const alphabetGrid = document.getElementById('alphabet-grid');
    const currentWordSpan = document.getElementById('current-word');
    const totalWordsSpan = document.getElementById('total-words');
    const correctWordsSpan = document.getElementById('correct-words');
    const wrongGuessesSpan = document.getElementById('wrong-guesses');
    const timerDisplay = document.getElementById('timer-display');
    const gameFeedback = document.getElementById('game-feedback');
    const gameResult = document.getElementById('gameResult');
    const resultTitle = document.getElementById('result-title');
    const finalCorrect = document.getElementById('final-correct');
    const finalAccuracy = document.getElementById('final-accuracy');
    const finalTime = document.getElementById('final-time');
    
    // Buttons
    const hintBtn = document.getElementById('hintBtn');
    const skipWordBtn = document.getElementById('skipWordBtn');
    const resetGameBtn = document.getElementById('resetGameBtn');
    const playAgainBtn = document.getElementById('playAgainBtn');
    const backToMenuBtn = document.getElementById('backToMenuBtn');
    const backToSettingsBtn = document.getElementById('backToSettingsBtn');
    
    // Hangman parts
    const hangmanParts = [
        document.getElementById('head'),
        document.getElementById('body'),
        document.getElementById('leftArm'),
        document.getElementById('rightArm'),
        document.getElementById('leftLeg'),
        document.getElementById('rightLeg')
    ];
    
    // Game Data
    const wordsData = JSON.parse(document.getElementById('hangmanWords').textContent);
    const gameSettings = JSON.parse(document.getElementById('gameSettings').textContent);
    
    // Game State
    let currentWordIndex = 0;
    let currentWord = '';
    let guessedLetters = [];
    let correctGuesses = 0;
    let wrongGuesses = 0;
    let totalCorrectWords = 0;
    let totalAttempts = 0;
    let totalWrongGuesses = 0; // Общий счетчик ошибок за всю игру
    let gameActive = true;
    let hintUsed = false;
    let gameStartTime = Date.now();
    let gameEndTime = null;
    let timerInterval = null;
    let timeRemaining = gameSettings.timerDuration;
    
    // Initialize game
    initializeGame();
    
    function initializeGame() {
        // Reset game state
        currentWordIndex = 0;
        totalCorrectWords = 0;
        totalAttempts = 0;
        totalWrongGuesses = 0;
        gameActive = true;
        gameStartTime = Date.now();
        gameEndTime = null;
        
        // Shuffle words
        shuffleArray(wordsData);
        
        // Create alphabet
        createAlphabet();
        
        // Start first word
        startNewWord();
        
        // Start timer if enabled
        if (gameSettings.timerDuration > 0) {
            timeRemaining = gameSettings.timerDuration;
            updateTimerDisplay();
            startTimer();
        } else if (gameSettings.enableStopwatch) {
            timeRemaining = 0;
            updateTimerDisplay();
            startStopwatch();
        }
        
        // Hide game result
        if (gameResult) gameResult.classList.remove('show');
        
        // Update UI
        updateStats();
    }
    
    function shuffleArray(array) {
        for (let i = array.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [array[i], array[j]] = [array[j], array[i]];
        }
        return array;
    }
    
    function createAlphabet() {
        if (!alphabetGrid) return;
        
        alphabetGrid.innerHTML = '';
        const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
        
        for (let letter of letters) {
            const btn = document.createElement('button');
            btn.className = 'letter-btn';
            btn.textContent = letter;
            btn.dataset.letter = letter;
            btn.addEventListener('click', () => guessLetter(letter));
            alphabetGrid.appendChild(btn);
        }
    }
    
    function startNewWord() {
        if (currentWordIndex >= wordsData.length) {
            endGame();
            return;
        }
        
        // Reset word state
        const wordData = wordsData[currentWordIndex];
        currentWord = wordData.word.toUpperCase();
        guessedLetters = [];
        correctGuesses = 0;
        wrongGuesses = 0;
        hintUsed = false;
        gameActive = true; // Активируем игру для нового слова
        
        // Reset hangman
        hangmanParts.forEach(part => {
            if (part) {
                part.classList.remove('show');
            }
        });
        
        // Reset hanging animation and overlay
        const hangmanBody = document.getElementById('hangman-body');
        const hangmanContainer = document.querySelector('.hangman-container');
        const gameOverOverlay = document.getElementById('game-over-overlay');
        if (hangmanBody) hangmanBody.classList.remove('hanging');
        if (hangmanContainer) hangmanContainer.classList.remove('game-over');
        if (gameOverOverlay) gameOverOverlay.classList.remove('show');
        
        // Reset alphabet
        document.querySelectorAll('.letter-btn').forEach(btn => {
            btn.className = 'letter-btn';
            btn.disabled = false;
        });
        
        // Reset hint display
        if (wordHint) {
            wordHint.classList.remove('show');
        }
        
        // Create word display
        createWordDisplay();
        
        // Show translation as hint
        if (wordHint) {
            wordHint.textContent = `Перевод: ${wordData.translation}`;
            wordHint.classList.add('show');
        }
        
        // Update stats
        updateStats();
        
        // Enable hint button
        if (hintBtn) {
            hintBtn.disabled = false;
            hintBtn.textContent = 'Подсказка';
        }
    }
    
    function createWordDisplay() {
        if (!wordDisplay) return;
        
        wordDisplay.innerHTML = '';
        
        for (let letter of currentWord) {
            const slot = document.createElement('div');
            slot.className = 'letter-slot';
            slot.dataset.letter = letter;
            
            if (letter === ' ') {
                slot.style.border = 'none';
                slot.style.width = '20px';
            } else if (guessedLetters.includes(letter)) {
                slot.textContent = letter;
                slot.classList.add('revealed');
            }
            
            wordDisplay.appendChild(slot);
        }
    }
    
    function guessLetter(letter) {
        if (!gameActive || guessedLetters.includes(letter)) return;
        
        const btn = document.querySelector(`[data-letter="${letter}"]`);
        if (!btn || btn.disabled) return;
        
        guessedLetters.push(letter);
        
        if (currentWord.includes(letter)) {
            // Correct guess
            btn.classList.add('correct');
            btn.disabled = true;
            
            // Reveal letters with animation delay
            const slots = document.querySelectorAll(`[data-letter="${letter}"]`);
            slots.forEach((slot, index) => {
                if (slot.classList.contains('letter-slot')) {
                    setTimeout(() => {
                        slot.textContent = letter;
                        slot.classList.add('revealed');
                    }, index * 150); // Delay each letter slightly for better effect
                    correctGuesses++;
                }
            });
            
            // Check if word is complete
            const uniqueLetters = [...new Set(currentWord.replace(/\s/g, ''))];
            const guessedUniqueLetters = uniqueLetters.filter(l => guessedLetters.includes(l));
            
            if (guessedUniqueLetters.length === uniqueLetters.length) {
                wordCompleted(true);
            }
        } else {
            // Wrong guess
            btn.classList.add('incorrect');
            btn.disabled = true;
            wrongGuesses++;
            totalWrongGuesses++; // Увеличиваем общий счетчик ошибок
            
            // Show hangman part with animation
            if (wrongGuesses <= hangmanParts.length && hangmanParts[wrongGuesses - 1]) {
                setTimeout(() => {
                    hangmanParts[wrongGuesses - 1].classList.add('show');
                    
                    // Add shake effect to the whole hangman container
                    const hangmanContainer = document.querySelector('.hangman-container');
                    hangmanContainer.style.animation = 'shake 0.5s ease-in-out';
                    setTimeout(() => {
                        hangmanContainer.style.animation = '';
                    }, 500);
                }, 200);
            }
            
            // Check if game over
            if (wrongGuesses >= hangmanParts.length) {
                wordCompleted(false);
            }
        }
        
        updateStats();
    }
    
    function wordCompleted(success) {
        totalAttempts++;
        // gameActive = false; // Moved this down after checks to allow interaction if needed by animation trigger
        
        if (success) {
            gameActive = false; // Deactivate game only on definite success here
            totalCorrectWords++;
            showFeedback('Отлично! Слово угадано!', 'success');
            createConfetti(50); // Add some confetti on success
            
            if (wrongGuesses === 0) {
                showFeedback('Идеально! Ни одной ошибки!', 'success');
            }
            
            setTimeout(() => {
                currentWordIndex++;
                if (currentWordIndex >= wordsData.length) {
                    endGame();
                } else {
                    startNewWord();
                }
            }, 2000);
        } else {
            gameActive = false; // Deactivate game on failure
            // Reveal the word
            document.querySelectorAll('.letter-slot').forEach(slot => {
                if (slot.dataset.letter && slot.dataset.letter !== ' ') {
                    slot.textContent = slot.dataset.letter;
                    slot.classList.add('revealed', 'lost-letter'); // Added 'lost-letter' for potential styling
                }
            });
            
            const uniqueLettersInWord = [...new Set(currentWord.replace(/\s/g, ''))];
            const correctlyGuessedUniqueLetters = uniqueLettersInWord.filter(l => guessedLetters.includes(l));
            const guessedRatio = uniqueLettersInWord.length > 0 ? (correctlyGuessedUniqueLetters.length / uniqueLettersInWord.length) : 0;

            let nextWordDelay = 2000; // Default delay for just losing the word

            if (guessedRatio < 0.5) {
                showFeedback('Меньше половины букв отгадано... Вы проиграли это слово.', 'error', 3000); // Longer feedback display
                startHangingAnimation();
                nextWordDelay = 5000; // Longer delay for the animation to play
            } else {
                showFeedback(`Слово не угадано: ${currentWord}`, 'error', 3000);
            }
            
            setTimeout(() => {
                currentWordIndex++;
                if (currentWordIndex >= wordsData.length) {
                    endGame();
                } else {
                    startNewWord();
                }
            }, nextWordDelay);
        }
    }
    
    function updateStats() {
        if (currentWordSpan) currentWordSpan.textContent = currentWordIndex + 1;
        if (totalWordsSpan) totalWordsSpan.textContent = wordsData.length;
        if (correctWordsSpan) correctWordsSpan.textContent = totalCorrectWords;
        if (wrongGuessesSpan) wrongGuessesSpan.textContent = totalWrongGuesses; // Показываем общий счетчик ошибок
    }
    
    function showHint() {
        if (hintUsed || !hintBtn) return;
        
        hintUsed = true;
        hintBtn.disabled = true;
        hintBtn.innerHTML = '<i class="fas fa-check"></i> Использована';
        
        const wordData = wordsData[currentWordIndex];
        let hintText = `Перевод: ${wordData.translation}`;
        
        if (wordData.definition) {
            hintText += `\nОпределение: ${wordData.definition}`;
        }
        
        if (wordData.example) {
            hintText += `\nПример: ${wordData.example}`;
        }
        
        if (wordHint) {
            wordHint.textContent = hintText;
            wordHint.classList.add('show');
        }
        showFeedback('Подсказка показана!', 'info');
    }
    
    function skipWord() {
        if (!gameActive) return;
        
        showFeedback(`Слово пропущено: ${currentWord}`, 'info');
        totalAttempts++;
        
        setTimeout(() => {
            currentWordIndex++;
            if (currentWordIndex >= wordsData.length) {
                endGame();
            } else {
                startNewWord();
            }
        }, 1500);
    }
    
    function showFeedback(message, type, duration = 2500) {
        if (!gameFeedback) return;
        
        gameFeedback.textContent = message;
        gameFeedback.className = `game-feedback show feedback-${type}`;
        
        setTimeout(() => {
            if (gameFeedback) gameFeedback.classList.remove('show');
        }, duration);
    }
    
    function startTimer() {
        if (timerInterval) clearInterval(timerInterval);
        
        timerInterval = setInterval(() => {
            timeRemaining--;
            updateTimerDisplay();
            
            if (timeRemaining <= 0) {
                clearInterval(timerInterval);
                endGame();
            }
        }, 1000);
    }
    
    function startStopwatch() {
        if (timerInterval) clearInterval(timerInterval);
        
        timerInterval = setInterval(() => {
            timeRemaining++;
            updateTimerDisplay();
        }, 1000);
    }
    
    function updateTimerDisplay() {
        if (!timerDisplay) return;
        
        if (gameSettings.enableStopwatch) {
            // Stopwatch - show time in MM:SS format
            const minutes = Math.floor(timeRemaining / 60);
            const seconds = timeRemaining % 60;
            timerDisplay.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            timerDisplay.className = 'stat-value';
            // Убираем inline стили - используем CSS классы
        } else if (gameSettings.timerDuration > 0) {
            // Timer - show remaining time
            timerDisplay.textContent = timeRemaining + 'с';
            
            // Update timer color based on time remaining
            timerDisplay.className = 'stat-value';
            
            if (timeRemaining <= 10) {
                timerDisplay.classList.remove('warning');
                timerDisplay.classList.add('danger');
            } else if (timeRemaining <= 30) {
                timerDisplay.classList.remove('danger');
                timerDisplay.classList.add('warning');
            } else {
                timerDisplay.classList.remove('danger', 'warning');
            }
        }
    }
    
    function endGame() {
        gameActive = false;
        gameEndTime = Date.now();
        if (timerInterval) clearInterval(timerInterval);

        const durationSeconds = Math.floor((gameEndTime - gameStartTime) / 1000);
        const accuracy = totalAttempts > 0 ? Math.round((totalCorrectWords / totalAttempts) * 100) : 0;

        if (resultTitle) {
            if (totalCorrectWords === wordsData.length) {
                resultTitle.textContent = 'Поздравляем! Все слова угаданы!';
                createConfetti(100); // Add confetti for a perfect game
            } else if (totalCorrectWords > 0) {
                resultTitle.textContent = 'Отличная работа!';
            } else {
                resultTitle.textContent = 'Игра окончена. Попробуйте еще раз!';
            }
        }
        
        if (finalCorrect) finalCorrect.textContent = totalCorrectWords;
        if (finalAccuracy) finalAccuracy.textContent = `${accuracy}%`;
        
        if (finalTime) {
            if (gameSettings.timerDuration > 0) {
                finalTime.textContent = `${gameSettings.timerDuration - timeRemaining} сек`;
            } else {
                const minutes = Math.floor(durationSeconds / 60);
                const seconds = durationSeconds % 60;
                finalTime.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            }
        }

        if (gameResult) {
            gameResult.classList.add('show');
        }

        // Stop any ongoing hanging animations
        const hangmanBody = document.getElementById('hangman-body');
        if (hangmanBody) hangmanBody.classList.remove('hanging');
        const hangmanContainer = document.querySelector('.hangman-container');
        if (hangmanContainer) hangmanContainer.classList.remove('game-over'); // ensure this class is added for fadeout
        
        // Optionally, add game-over class for fade-out if it's not added elsewhere
        // if (hangmanContainer) hangmanContainer.classList.add('game-over'); 
    }
    
    function createConfetti(count) {
        const colors = ['#f94144', '#f3722c', '#f8961e', '#f9c74f', '#90be6d', '#43aa8b', '#577590', '#4361ee', '#3a0ca3', '#7209b7', '#b5179e'];
        
        for (let i = 0; i < count; i++) {
            const confetti = document.createElement('div');
            confetti.classList.add('confetti');
            confetti.style.left = Math.random() * 100 + 'vw';
            confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
            confetti.style.width = Math.random() * 12 + 8 + 'px';
            confetti.style.height = Math.random() * 12 + 8 + 'px';
            confetti.style.animationDuration = Math.random() * 3 + 2 + 's';
            document.body.appendChild(confetti);
            
            setTimeout(() => {
                confetti.remove();
            }, 5000);
        }
    }
    
    function startHangingAnimation() {
        const hangmanBody = document.getElementById('hangman-body');
        const hangmanContainer = document.querySelector('.hangman-container');
        // const gameOverOverlay = document.getElementById('game-over-overlay'); // This ID is from 'ideas'

        if (hangmanBody && hangmanContainer) {
            hangmanBody.classList.add('hanging');
            hangmanContainer.classList.add('game-over'); // This applies the fade-out

            // If you add an element with id 'game-over-overlay' to your game_hangman_improved.html,
            // you can uncomment and use the following:
            // if (gameOverOverlay) {
            //     setTimeout(() => {
            //         gameOverOverlay.classList.add('show');
            //     }, 1000); 
            // }
        }
    }
    
    // Event Listeners
    if (hintBtn) hintBtn.addEventListener('click', showHint);
    if (skipWordBtn) skipWordBtn.addEventListener('click', skipWord);
    if (resetGameBtn) resetGameBtn.addEventListener('click', initializeGame);
    if (playAgainBtn) playAgainBtn.addEventListener('click', initializeGame);
    
    // Back to settings button
    if (backToSettingsBtn) {
        backToSettingsBtn.addEventListener('click', () => {
            window.location.href = '/games/hangman/select';
        });
    }
    
    // Back to menu button
    if (backToMenuBtn) {
        backToMenuBtn.addEventListener('click', () => {
            window.location.href = '/games/hangman/select';
        });
    }
    
    // Keyboard support
    document.addEventListener('keydown', function(event) {
        if (!gameActive) return;
        
        const key = event.key.toUpperCase();
        if (key >= 'A' && key <= 'Z') {
            guessLetter(key);
        }
    });
});
});