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
        gameResult.classList.remove('show');
        
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
        
        // Reset hangman
        hangmanParts.forEach(part => part.style.display = 'none');
        
        // Reset alphabet
        document.querySelectorAll('.letter-btn').forEach(btn => {
            btn.className = 'letter-btn';
            btn.disabled = false;
        });
        
        // Create word display
        createWordDisplay();
        
        // Show translation as hint
        wordHint.textContent = `Перевод: ${wordData.translation}`;
        
        // Update stats
        updateStats();
        
        // Enable hint button
        hintBtn.disabled = false;
        hintBtn.textContent = 'Подсказка';
    }
    
    function createWordDisplay() {
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
        
        guessedLetters.push(letter);
        const btn = document.querySelector(`[data-letter="${letter}"]`);
        
        if (currentWord.includes(letter)) {
            // Correct guess
            btn.classList.add('correct');
            btn.disabled = true;
            
            // Reveal letters
            const slots = document.querySelectorAll(`[data-letter="${letter}"]`);
            slots.forEach(slot => {
                if (slot.classList.contains('letter-slot')) {
                    slot.textContent = letter;
                    slot.classList.add('revealed');
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
            
            // Show hangman part
            if (wrongGuesses <= hangmanParts.length) {
                hangmanParts[wrongGuesses - 1].style.display = 'block';
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
        
        if (success) {
            totalCorrectWords++;
            showFeedback('Отлично! Слово угадано!', 'success');
            
            // Add bonus points for fewer wrong guesses
            if (wrongGuesses === 0) {
                showFeedback('Идеально! Ни одной ошибки!', 'success');
            }
        } else {
            showFeedback(`Слово было: ${currentWord}`, 'error');
            
            // Reveal the word
            document.querySelectorAll('.letter-slot').forEach(slot => {
                if (slot.dataset.letter && slot.dataset.letter !== ' ') {
                    slot.textContent = slot.dataset.letter;
                    slot.classList.add('revealed');
                }
            });
        }
        
        // Move to next word after delay
        setTimeout(() => {
            currentWordIndex++;
            startNewWord();
        }, 2000);
    }
    
    function updateStats() {
        currentWordSpan.textContent = currentWordIndex + 1;
        correctWordsSpan.textContent = totalCorrectWords;
        wrongGuessesSpan.textContent = wrongGuesses;
    }
    
    function showHint() {
        if (hintUsed) return;
        
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
        
        wordHint.textContent = hintText;
        showFeedback('Подсказка показана!', 'info');
    }
    
    function skipWord() {
        if (!gameActive) return;
        
        showFeedback(`Слово пропущено: ${currentWord}`, 'info');
        totalAttempts++;
        
        setTimeout(() => {
            currentWordIndex++;
            startNewWord();
        }, 1500);
    }
    
    function showFeedback(message, type) {
        gameFeedback.textContent = message;
        gameFeedback.className = `game-feedback show ${type}`;
        
        setTimeout(() => {
            gameFeedback.classList.remove('show');
        }, 2500);
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
        } else {
            // Timer - show remaining time
            timerDisplay.textContent = timeRemaining + 'с';
            
            // Update timer color based on time remaining
            timerDisplay.className = 'stat-value';
            if (timeRemaining <= 10) {
                timerDisplay.classList.add('danger');
            } else if (timeRemaining <= 30) {
                timerDisplay.classList.add('warning');
            }
        }
    }
    
    function endGame() {
        gameActive = false;
        gameEndTime = Date.now();
        
        if (timerInterval) {
            clearInterval(timerInterval);
        }
        
        // Calculate stats
        const gameTimeSeconds = Math.floor((gameEndTime - gameStartTime) / 1000);
        const accuracyPercentage = totalAttempts > 0 ? Math.round((totalCorrectWords / totalAttempts) * 100) : 0;
        
        // Update result display
        finalCorrect.textContent = totalCorrectWords;
        finalAccuracy.textContent = accuracyPercentage + '%';
        
        if (finalTime) {
            if (gameSettings.enableStopwatch) {
                const minutes = Math.floor(gameTimeSeconds / 60);
                const seconds = gameTimeSeconds % 60;
                finalTime.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            } else {
                finalTime.textContent = gameTimeSeconds + 'с';
            }
        }
        
        // Set result title
        if (accuracyPercentage === 100) {
            resultTitle.textContent = '🎉 Идеальный результат!';
            createConfetti(100);
        } else if (accuracyPercentage >= 80) {
            resultTitle.textContent = '🌟 Отличная работа!';
        } else if (accuracyPercentage >= 60) {
            resultTitle.textContent = '👍 Хорошо!';
        } else {
            resultTitle.textContent = '💪 Попробуйте еще раз!';
        }
        
        // Show result
        gameResult.classList.add('show');
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
    
    // Event Listeners
    hintBtn.addEventListener('click', showHint);
    skipWordBtn.addEventListener('click', skipWord);
    resetGameBtn.addEventListener('click', initializeGame);
    playAgainBtn.addEventListener('click', initializeGame);
    
    // Keyboard support
    document.addEventListener('keydown', function(event) {
        if (!gameActive) return;
        
        const key = event.key.toUpperCase();
        if (key >= 'A' && key <= 'Z') {
            guessLetter(key);
        }
    });
    
    // Back to settings button
    if (backToSettingsBtn) {
        backToSettingsBtn.addEventListener('click', () => {
            const params = new URLSearchParams();
            params.append('words', '{{ num_words }}');
            params.append('difficulty', '{{ difficulty }}');
            {% if timer_duration > 0 %}
            params.append('timer', '{{ timer_duration }}');
            {% elif enable_stopwatch %}
            params.append('stopwatch', 'true');
            {% endif %}
            
            window.location.href = '{{ url_for("hangman_select_module") }}?' + params.toString();
        });
    }
});