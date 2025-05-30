document.addEventListener('DOMContentLoaded', function() {
    const sentencesDataElement = document.getElementById('sentenceScrambleData');
    const translationHintArea = document.getElementById('translation-hint-area');
    const userSentenceArea = document.getElementById('user-sentence-area');
    const scrambledWordsPool = document.getElementById('scrambled-words-pool');
    const checkAnswerBtn = document.getElementById('checkAnswerBtnScramble');
    const nextSentenceBtn = document.getElementById('nextSentenceBtnScramble');
    const resetCurrentBtn = document.getElementById('resetCurrentBtnScramble');
    const gameFeedback = document.getElementById('game-feedback-scramble');
    const sentenceCounterDisplay = document.getElementById('sentence-counter');

    let sentences = [];
    let currentSentenceIndex = 0;
    let currentWordsInPool = [];
    let currentWordsInUserArea = [];

    if (sentencesDataElement) {
        try {
            sentences = JSON.parse(sentencesDataElement.textContent);
        } catch (e) {
            console.error("Error parsing sentences data:", e);
            if(gameFeedback) gameFeedback.textContent = "Ошибка загрузки предложений для игры.";
            // Disable buttons if data is bad
            if(checkAnswerBtn) checkAnswerBtn.disabled = true;
            if(nextSentenceBtn) nextSentenceBtn.disabled = true;
            if(resetCurrentBtn) resetCurrentBtn.disabled = true;
            return;
        }
    } else {
        if(gameFeedback) gameFeedback.textContent = "Не найдены данные для игры.";
        return;
    }

    function shuffleArray(array) {
        for (let i = array.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [array[i], array[j]] = [array[j], array[i]];
        }
        return array;
    }

    function loadSentence(index) {
        if (index >= sentences.length || index < 0) {
            userSentenceArea.innerHTML = '';
            scrambledWordsPool.innerHTML = '';
            translationHintArea.textContent = '';
            gameFeedback.textContent = "Все предложения пройдены!";
            if (sentenceCounterDisplay) sentenceCounterDisplay.textContent = `Завершено ${sentences.length}/${sentences.length}`;
            if (checkAnswerBtn) checkAnswerBtn.style.display = 'none';
            if (resetCurrentBtn) resetCurrentBtn.style.display = 'none';
            if (nextSentenceBtn) nextSentenceBtn.style.display = 'none';
            return;
        }

        const sentence = sentences[index];
        translationHintArea.textContent = sentence.translation ? `Подсказка: ${sentence.translation}` : 'Перевод отсутствует.';

        currentWordsInUserArea = [];
        userSentenceArea.innerHTML = '';

        const words = sentence.text.replace(/[.,!?;:]/g, '').split(/\s+/).filter(w => w.length > 0);
        currentWordsInPool = shuffleArray([...words]); // Keep a copy for reset

        renderWordPool();
        renderUserSentence();

        if (gameFeedback) gameFeedback.textContent = '';
        if (checkAnswerBtn) {
            checkAnswerBtn.disabled = false;
            checkAnswerBtn.style.display = 'inline-block';
        }
        if (nextSentenceBtn) nextSentenceBtn.style.display = 'none'; // Hide until answered correctly
        if (resetCurrentBtn) resetCurrentBtn.disabled = false;
        if (sentenceCounterDisplay) sentenceCounterDisplay.textContent = `Предложение ${index + 1} из ${sentences.length}`;
    }

    function renderWordPool() {
        scrambledWordsPool.innerHTML = '';
        currentWordsInPool.forEach((word, idx) => {
            const wordToken = document.createElement('span');
            wordToken.classList.add('word-token');
            wordToken.textContent = word;
            wordToken.dataset.originalIndex = idx; // To put it back if needed, or just by text
            wordToken.addEventListener('click', handlePoolWordClick);
            scrambledWordsPool.appendChild(wordToken);
        });
    }

    function renderUserSentence() {
        userSentenceArea.innerHTML = '';
        currentWordsInUserArea.forEach((wordData, idx) => {
            const wordToken = document.createElement('span');
            wordToken.classList.add('word-token');
            wordToken.textContent = wordData.text;
            wordToken.dataset.poolIndex = wordData.poolIndex; // Store where it came from
            wordToken.addEventListener('click', handleUserSentenceWordClick);
            userSentenceArea.appendChild(wordToken);
        });
    }

    function handlePoolWordClick(event) {
        const clickedWord = event.target.textContent;
        const originalPoolIndex = parseInt(event.target.dataset.originalIndex); // We don't really need this if we remove by text

        // Remove from pool visually and from array
        currentWordsInPool.splice(currentWordsInPool.indexOf(clickedWord), 1);

        // Add to user sentence area
        currentWordsInUserArea.push({text: clickedWord, poolIndex: originalPoolIndex}); // Storing original index for simple reset

        renderWordPool();
        renderUserSentence();
        if (checkAnswerBtn) checkAnswerBtn.disabled = false; // Enable check button
    }

    function handleUserSentenceWordClick(event) {
        const clickedWordText = event.target.textContent;
        const poolIndex = parseInt(event.target.dataset.poolIndex); // Get the original index in the pool

        // Remove from user sentence area
        currentWordsInUserArea = currentWordsInUserArea.filter(wordData => wordData.text !== clickedWordText || wordData.poolIndex !== poolIndex); // Ensure correct instance is removed if duplicate words

        // Add back to pool (could be smarter about original position, but for now just add back)
        currentWordsInPool.push(clickedWordText); // Re-add the text

        shuffleArray(currentWordsInPool); // Re-shuffle pool for better UX
        renderWordPool();
        renderUserSentence();
        if (checkAnswerBtn) checkAnswerBtn.disabled = currentWordsInUserArea.length === 0;
    }

    if (checkAnswerBtn) {
        checkAnswerBtn.addEventListener('click', function() {
            if (currentWordsInUserArea.length === 0) {
                if(gameFeedback) gameFeedback.textContent = "Пожалуйста, соберите предложение.";
                return;
            }
            const userAnswer = currentWordsInUserArea.map(wd => wd.text).join(' ');
            const correctAnswer = sentences[currentSentenceIndex].text.replace(/[.,!?;:]/g, '');

            if (userAnswer.toLowerCase() === correctAnswer.toLowerCase()) { // Case-insensitive check
                if(gameFeedback) gameFeedback.textContent = "Правильно!";
                gameFeedback.style.color = 'var(--success)';
                this.disabled = true;
                if (resetCurrentBtn) resetCurrentBtn.disabled = true;
                if (nextSentenceBtn) nextSentenceBtn.style.display = 'inline-block';
                if (currentSentenceIndex === sentences.length - 1 && nextSentenceBtn) {
                     nextSentenceBtn.textContent = "Завершить игру"; // Or hide and show a different button
                }
            } else {
                if(gameFeedback) gameFeedback.textContent = "Неправильно. Попробуйте еще раз.";
                gameFeedback.style.color = 'var(--danger)';
            }
        });
    }

    if (nextSentenceBtn) {
        nextSentenceBtn.addEventListener('click', function() {
            currentSentenceIndex++;
            loadSentence(currentSentenceIndex);
            if(gameFeedback) gameFeedback.textContent = ''; // Clear feedback
            gameFeedback.style.color = 'var(--text)'; // Reset color
            this.style.display = 'none'; // Hide next button until current is solved
            if (checkAnswerBtn) checkAnswerBtn.disabled = false;
            if (resetCurrentBtn) resetCurrentBtn.disabled = false;
        });
    }

    if (resetCurrentBtn) {
        resetCurrentBtn.addEventListener('click', function() {
            // Reset current sentence: put all words from user area back to pool and reshuffle pool
            const sentence = sentences[currentSentenceIndex];
            const words = sentence.text.replace(/[.,!?;:]/g, '').split(/\s+/).filter(w => w.length > 0);
            currentWordsInPool = shuffleArray([...words]);
            currentWordsInUserArea = [];

            renderWordPool();
            renderUserSentence();
            if(gameFeedback) gameFeedback.textContent = 'Предложение сброшено.';
            gameFeedback.style.color = 'var(--text)';
            if (checkAnswerBtn) checkAnswerBtn.disabled = false;
            if (nextSentenceBtn) nextSentenceBtn.style.display = 'none';
        });
    }

    // Initial load
    if (sentences.length > 0) {
        loadSentence(currentSentenceIndex);
    } else {
        if(gameFeedback) gameFeedback.textContent = "В этом модуле нет предложений для игры.";
        if(sentenceCounterDisplay) sentenceCounterDisplay.textContent = "0/0";
        if (checkAnswerBtn) checkAnswerBtn.disabled = true;
        if (resetCurrentBtn) resetCurrentBtn.disabled = true;
        if (nextSentenceBtn) nextSentenceBtn.style.display = 'none';
    }
});
