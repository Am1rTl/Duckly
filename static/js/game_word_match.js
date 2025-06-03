document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const matchArea = document.querySelector('.match-area');
    const wordsColumn = document.getElementById('words-column');
    const translationsColumn = document.getElementById('translations-column');
    const connectionsSvg = document.getElementById('connections-svg');
    const originalWordsDataEl = document.getElementById('wordMatchOriginalData');
    const jumbledWordsEl = document.getElementById('jumbledWords');
    const jumbledTranslationsEl = document.getElementById('jumbledTranslations');
    const gameSettingsEl = document.getElementById('gameSettings');
    const finishGameBtn = document.getElementById('finishGameBtn');
    const resetGameBtn = document.getElementById('resetGameBtn');
    const scoreDisplay = document.getElementById('current-score');
    const totalPairsDisplay = document.getElementById('total-pairs');
    const timerDisplay = document.getElementById('timer-display');
    const gameFeedback = document.getElementById('game-feedback');
    const gameResult = document.getElementById('gameResult');
    const finalScore = document.getElementById('finalScore');
    const finalAccuracy = document.getElementById('finalAccuracy');
    const finalTime = document.getElementById('finalTime');
    const playAgainBtn = document.getElementById('playAgainBtn');

    // SVG namespace
    const svgNS = 'http://www.w3.org/2000/svg';

    let originalWords = [];
    let jumbledWords = [];
    let jumbledTranslations = [];
    let gameSettings = {};

    let selectedWordItem = null;
    let selectedTranslationItem = null;
    let currentScore = 0;
    let totalPairs = 0;
    let timerInterval = null;
    let timeRemaining = 0;
    let gameActive = true;
    let attemptCount = 0;
    let correctPairs = 0;
    let gameStartTime = Date.now();
    let gameEndTime = null;
    let connections = []; // Array to store SVG connections
    let gameCompleted = false;

    function parseJsonData() {
        try {
            if (originalWordsDataEl) originalWords = JSON.parse(originalWordsDataEl.textContent);
            if (jumbledWordsEl) jumbledWords = JSON.parse(jumbledWordsEl.textContent);
            if (jumbledTranslationsEl) jumbledTranslations = JSON.parse(jumbledTranslationsEl.textContent);
            if (gameSettingsEl) gameSettings = JSON.parse(gameSettingsEl.textContent);
            
            totalPairs = originalWords.length;
            timeRemaining = gameSettings.timerDuration || 0;
            
            return true;
        } catch (e) {
            console.error("Error parsing game data:", e);
            if(gameFeedback) showFeedback("Ошибка загрузки данных для игры.", "error");
            return false;
        }
    }

    // Function to shuffle array (Fisher-Yates algorithm)
    function shuffleArray(array) {
        for (let i = array.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [array[i], array[j]] = [array[j], array[i]];
        }
        return array;
    }

    function createMatchItem(itemData, type) {
        const itemDiv = document.createElement('div');
        itemDiv.classList.add('match-item');
        itemDiv.textContent = itemData.text;
        itemDiv.dataset.id = itemData.id;
        itemDiv.dataset.type = type;
        
        // Add subtle animation
        itemDiv.style.opacity = '0';
        itemDiv.style.transform = 'translateY(20px)';
        setTimeout(() => {
            itemDiv.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            itemDiv.style.opacity = '1';
            itemDiv.style.transform = 'translateY(0)';
        }, 50);
        
        return itemDiv;
    }

    function initializeGame() {
        // Reset game state
        selectedWordItem = null;
        selectedTranslationItem = null;
        currentScore = 0;
        attemptCount = 0;
        correctPairs = 0;
        gameActive = true;
        gameStartTime = Date.now();
        gameEndTime = null;
        connections = [];
        gameCompleted = false;
        
        // Update UI
        if (scoreDisplay) scoreDisplay.textContent = "0";
        if (totalPairsDisplay) totalPairsDisplay.textContent = totalPairs;
        
        // Reset finish button
        if (finishGameBtn) {
            finishGameBtn.disabled = false;
            finishGameBtn.textContent = 'Завершить игру';
        }
        
        // Clear columns
        wordsColumn.innerHTML = '<h3>Слова</h3>';
        translationsColumn.innerHTML = '<h3>Переводы</h3>';
        
        // Remove all SVG connections
        clearAllConnections();
        
        // Shuffle cards before each new game
        jumbledWords = shuffleArray([...jumbledWords]);
        jumbledTranslations = shuffleArray([...jumbledTranslations]);
        
        // Populate columns
        jumbledWords.forEach(wordItem => {
            wordsColumn.appendChild(createMatchItem(wordItem, 'word'));
        });
        
        jumbledTranslations.forEach(transItem => {
            translationsColumn.appendChild(createMatchItem(transItem, 'translation'));
        });
        
        // Hide game result
        if (gameResult) gameResult.classList.remove('show');
        
        // Hide feedback
        if (gameFeedback) {
            gameFeedback.classList.remove('show');
            gameFeedback.className = '';
        }
        
        // Start timer or stopwatch if enabled
        if (gameSettings.timerDuration > 0) {
            timeRemaining = gameSettings.timerDuration;
            updateTimerDisplay();
            startTimer();
        } else if (gameSettings.enableStopwatch) {
            timeRemaining = 0;
            updateTimerDisplay();
            startStopwatch();
        }
        
        // Add event listeners to match items
        addEventListenersToMatchItems();
    }

    function addEventListenersToMatchItems() {
        const matchItems = document.querySelectorAll('.match-item');
        matchItems.forEach(item => {
            item.addEventListener('click', handleMatchItemClick);
        });
    }

    function handleMatchItemClick(event) {
        if (!gameActive) return;
        
        const clickedItem = event.currentTarget;
        const itemType = clickedItem.dataset.type;
        const itemId = clickedItem.dataset.id;
        
        // If card is already paired - break connection
        if (clickedItem.classList.contains('paired')) {
            breakConnection(clickedItem);
            return;
        }
        
        if (itemType === 'word') {
            // Remove selection from previous selected card in this column
            if (selectedWordItem) {
                selectedWordItem.classList.remove('selected');
            }
            
            // Select new card
            clickedItem.classList.add('selected');
            selectedWordItem = clickedItem;
            
            // If translation is selected - create connection
            if (selectedTranslationItem) {
                createConnection();
            }
        } else if (itemType === 'translation') {
            // Remove selection from previous selected card in this column
            if (selectedTranslationItem) {
                selectedTranslationItem.classList.remove('selected');
            }
            
            // Select new card
            clickedItem.classList.add('selected');
            selectedTranslationItem = clickedItem;
            
            // If word is selected - create connection
            if (selectedWordItem) {
                createConnection();
            }
        }
    }

    function createConnection() {
        // Check that both cards are selected
        if (!selectedWordItem || !selectedTranslationItem) return;
        
        // Get card coordinates
        const wordRect = selectedWordItem.getBoundingClientRect();
        const transRect = selectedTranslationItem.getBoundingClientRect();
        const gameAreaRect = matchArea.getBoundingClientRect();
        
        // Calculate positions relative to game area
        const wordX = wordRect.left + wordRect.width - gameAreaRect.left;
        const wordY = wordRect.top + wordRect.height / 2 - gameAreaRect.top;
        const transX = transRect.left - gameAreaRect.left;
        const transY = transRect.top + transRect.height / 2 - gameAreaRect.top;
        
        // Create Bezier curve for beautiful connection
        const path = document.createElementNS(svgNS, 'path');
        const midX = (wordX + transX) / 2;
        
        // Form Bezier curve path
        const pathData = `M ${wordX} ${wordY} C ${midX} ${wordY}, ${midX} ${transY}, ${transX} ${transY}`;
        path.setAttribute('d', pathData);
        path.classList.add('connection-curve');
        
        // Check if cards are correctly matched
        const wordId = selectedWordItem.dataset.id;
        const translationId = selectedTranslationItem.dataset.id;
        const isCorrect = wordId === translationId;
        
        attemptCount++;
        
        // Don't show correctness immediately - just mark as neutral
        path.classList.add('neutral');
        
        // Add path to SVG
        connectionsSvg.appendChild(path);
        
        // Store connection information
        connections.push({
            element: path,
            wordItem: selectedWordItem,
            translationItem: selectedTranslationItem,
            isCorrect: isCorrect
        });
        
        // Mark cards as paired (neutral style)
        selectedWordItem.classList.add('paired');
        selectedTranslationItem.classList.add('paired');
        
        // Reset selection
        selectedWordItem.classList.remove('selected');
        selectedTranslationItem.classList.remove('selected');
        selectedWordItem = null;
        selectedTranslationItem = null;
        
        // Update score
        currentScore++;
        if (scoreDisplay) scoreDisplay.textContent = currentScore;
        
        // Check if all words are paired
        if (currentScore === totalPairs) {
            // All words are paired - show results and end game
            setTimeout(() => {
                revealResults();
                setTimeout(() => {
                    endGame(true);
                }, 2000); // Show results for 2 seconds before showing final modal
            }, 500); // Small delay to let the last connection animation finish
        }
    }

    function breakConnection(card) {
        // Don't allow breaking connections after game is completed
        if (gameCompleted) return;
        
        // Find connection containing this card
        const connectionIndex = connections.findIndex(conn => 
            conn.wordItem === card || conn.translationItem === card
        );
        
        if (connectionIndex === -1) return;
        
        const connection = connections[connectionIndex];
        
        // Remove visual connection
        connection.element.remove();
        
        // Remove paired and style classes
        connection.wordItem.classList.remove('paired', 'correct-paired', 'incorrect-paired');
        connection.translationItem.classList.remove('paired', 'correct-paired', 'incorrect-paired');
        
        // If connection was correct, decrease correct pairs count
        if (connection.isCorrect) {
            correctPairs--;
        }
        
        // Decrease total score
        currentScore--;
        if (scoreDisplay) scoreDisplay.textContent = currentScore;
        
        // Remove connection from array
        connections.splice(connectionIndex, 1);
        
        // Show feedback
        showFeedback('Связь разорвана', 'info');
    }

    function clearAllConnections() {
        // Remove all paths from SVG (except gradients)
        const paths = connectionsSvg.querySelectorAll('path');
        paths.forEach(path => path.remove());
        
        // Clear connections array
        connections = [];
    }

    function showFeedback(message, type) {
        if (!gameFeedback) return;
        
        gameFeedback.textContent = message;
        gameFeedback.className = 'feedback-' + type;
        gameFeedback.classList.add('show');
        
        // Hide after delay
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
                endGame(false);
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
            timerDisplay.className = ''; // Remove color classes for stopwatch
        } else {
            // Timer - show remaining time
            timerDisplay.textContent = timeRemaining + 'с';
            
            // Update timer color based on time remaining
            timerDisplay.className = '';
            if (timeRemaining <= 10) {
                timerDisplay.classList.add('danger');
            } else if (timeRemaining <= 30) {
                timerDisplay.classList.add('warning');
            }
        }
    }

    function revealResults() {
        if (gameCompleted) return;
        
        correctPairs = 0; // Reset and recalculate
        
        // Go through all connections and reveal their correctness
        connections.forEach(connection => {
            if (connection.isCorrect) {
                correctPairs++;
                // Mark as correct
                connection.element.classList.remove('neutral');
                connection.element.classList.add('correct');
                connection.wordItem.classList.add('correct-paired');
                connection.translationItem.classList.add('correct-paired');
            } else {
                // Mark as incorrect
                connection.element.classList.remove('neutral');
                connection.element.classList.add('incorrect');
                connection.wordItem.classList.add('incorrect-paired');
                connection.translationItem.classList.add('incorrect-paired');
            }
        });
        
        // Show feedback
        showFeedback(`Правильных пар: ${correctPairs} из ${currentScore}`, 'info');
        
        gameCompleted = true;
        
        // Disable finish button
        if (finishGameBtn) {
            finishGameBtn.disabled = true;
            finishGameBtn.textContent = 'Игра завершена';
        }
    }

    function endGame(completed) {
        gameActive = false;
        gameEndTime = Date.now();
        
        if (timerInterval) {
            clearInterval(timerInterval);
        }
        
        // Reveal correct and incorrect pairs if not already revealed
        if (!gameCompleted) {
            revealResults();
        }
        
        // Calculate stats
        const gameTimeSeconds = Math.floor((gameEndTime - gameStartTime) / 1000);
        const accuracyPercentage = attemptCount > 0 ? Math.round((correctPairs / attemptCount) * 100) : 0;
        
        // Update result display
        if (finalScore) finalScore.textContent = correctPairs;
        if (finalAccuracy) finalAccuracy.textContent = accuracyPercentage + '%';
        
        // Display time based on mode
        if (finalTime) {
            if (gameSettings.enableStopwatch) {
                // For stopwatch show time in MM:SS format
                const minutes = Math.floor(gameTimeSeconds / 60);
                const seconds = gameTimeSeconds % 60;
                finalTime.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            } else {
                // For timer show time in seconds
                finalTime.textContent = gameTimeSeconds + 'с';
            }
        }
        
        // Show result with animation
        if (gameResult) gameResult.classList.add('show');
        
        // Show appropriate feedback
        if (completed) {
            showFeedback('Игра завершена! Проверьте свои результаты.', 'info');
            if (correctPairs === totalPairs) {
                createConfetti(150); // Celebration confetti for perfect score
            }
        } else {
            showFeedback('Время истекло! Игра завершена.', 'info');
        }
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
            confetti.style.setProperty('--random-x', Math.random());
            confetti.style.setProperty('--random-rot', Math.random());
            confetti.style.animationDuration = Math.random() * 3 + 2 + 's';
            document.body.appendChild(confetti);
            
            // Remove confetti after animation
            setTimeout(() => {
                confetti.remove();
            }, 5000);
        }
    }

    // Event Listeners
    if (finishGameBtn) {
        finishGameBtn.addEventListener('click', () => {
            // Finish game and reveal results
            if (currentScore > 0 && !gameCompleted) {
                revealResults();
                setTimeout(() => {
                    endGame(true);
                }, 2000); // Show results for 2 seconds before showing final modal
            } else {
                showFeedback('Сначала сопоставьте слова с их переводами!', 'info');
            }
        });
    }

    if (resetGameBtn) {
        resetGameBtn.addEventListener('click', () => {
            initializeGame();
        });
    }

    if (playAgainBtn) {
        playAgainBtn.addEventListener('click', () => {
            initializeGame();
        });
    }

    // Initialization
    if (parseJsonData()) {
        if (originalWords.length > 0) {
            initializeGame();
        } else {
            showFeedback("Нет слов для игры в этом модуле.", "error");
            if (finishGameBtn) finishGameBtn.disabled = true;
            if (resetGameBtn) resetGameBtn.disabled = true;
        }
    }
});
