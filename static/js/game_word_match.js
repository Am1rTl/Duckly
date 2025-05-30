document.addEventListener('DOMContentLoaded', function() {
    const wordsColumn = document.getElementById('words-column');
    const translationsColumn = document.getElementById('translations-column');
    const originalWordsDataEl = document.getElementById('wordMatchOriginalData');
    const jumbledWordsEl = document.getElementById('jumbledWords');
    const jumbledTranslationsEl = document.getElementById('jumbledTranslations');
    const checkAnswersBtn = document.getElementById('checkAnswersBtn');
    const resetGameBtn = document.getElementById('resetGameBtn');
    const scoreDisplay = document.getElementById('current-score');
    const totalPairsDisplay = document.getElementById('total-pairs');
    const gameFeedback = document.getElementById('game-feedback');

    let originalWords = [];
    let jumbledWords = [];
    let jumbledTranslations = [];

    let selectedWord = null; // { id: ..., element: ... }
    let selectedTranslation = null; // { id: ..., element: ... }
    let score = 0;
    let pairsMade = 0;

    function parseJsonData() {
        try {
            if (originalWordsDataEl) originalWords = JSON.parse(originalWordsDataEl.textContent);
            if (jumbledWordsEl) jumbledWords = JSON.parse(jumbledWordsEl.textContent);
            if (jumbledTranslationsEl) jumbledTranslations = JSON.parse(jumbledTranslationsEl.textContent);
            return true;
        } catch (e) {
            console.error("Error parsing game data:", e);
            if(gameFeedback) gameFeedback.textContent = "Ошибка загрузки данных для игры.";
            return false;
        }
    }

    function createMatchItem(itemData, type) {
        const itemDiv = document.createElement('div');
        itemDiv.classList.add('match-item');
        itemDiv.textContent = itemData.text;
        itemDiv.dataset.id = itemData.id; // This ID is the original word's ID
        itemDiv.dataset.type = type; // 'word' or 'translation'
        itemDiv.addEventListener('click', handleItemClick);
        return itemDiv;
    }

    function populateColumns() {
        if (!wordsColumn || !translationsColumn) return;
        wordsColumn.innerHTML = '<h3>Слова</h3>'; // Clear previous items but keep header
        translationsColumn.innerHTML = '<h3>Переводы</h3>';

        jumbledWords.forEach(wordItem => {
            wordsColumn.appendChild(createMatchItem(wordItem, 'word'));
        });
        jumbledTranslations.forEach(transItem => {
            translationsColumn.appendChild(createMatchItem(transItem, 'translation'));
        });
        if (totalPairsDisplay) totalPairsDisplay.textContent = originalWords.length;
        if (scoreDisplay) scoreDisplay.textContent = "0";
        if (gameFeedback) gameFeedback.textContent = "";
        pairsMade = 0;
        score = 0;
    }

    function handleItemClick(event) {
        const clickedItem = event.target;
        if (clickedItem.classList.contains('paired') || clickedItem.classList.contains('incorrect-paired')) return;

        const type = clickedItem.dataset.type;
        const id = clickedItem.dataset.id;

        if (type === 'word') {
            if (selectedWord && selectedWord.element === clickedItem) { // Deselect
                selectedWord.element.classList.remove('selected');
                selectedWord = null;
            } else {
                if (selectedWord) selectedWord.element.classList.remove('selected');
                clickedItem.classList.add('selected');
                selectedWord = { id: id, element: clickedItem };
            }
        } else if (type === 'translation') {
            if (selectedTranslation && selectedTranslation.element === clickedItem) { // Deselect
                selectedTranslation.element.classList.remove('selected');
                selectedTranslation = null;
            } else {
                if (selectedTranslation) selectedTranslation.element.classList.remove('selected');
                clickedItem.classList.add('selected');
                selectedTranslation = { id: id, element: clickedItem };
            }
        }
        checkPair();
    }

    function checkPair() {
        if (selectedWord && selectedTranslation) {
            pairsMade++;
            if (selectedWord.id === selectedTranslation.id) { // Correct pair based on original word ID
                score++;
                selectedWord.element.classList.add('paired');
                selectedTranslation.element.classList.add('paired');
                selectedWord.element.classList.remove('selected');
                selectedTranslation.element.classList.remove('selected');
                if(gameFeedback) gameFeedback.textContent = "Верно!";
            } else {
                selectedWord.element.classList.add('incorrect-paired');
                selectedTranslation.element.classList.add('incorrect-paired');
                selectedWord.element.classList.remove('selected');
                selectedTranslation.element.classList.remove('selected');
                if(gameFeedback) gameFeedback.textContent = "Неверно!";
                // Temporarily show incorrect, then revert
                setTimeout(() => {
                    selectedWord.element.classList.remove('incorrect-paired');
                    selectedTranslation.element.classList.remove('incorrect-paired');
                    // selectedWord and selectedTranslation are reset below, so no need to remove 'selected' again
                }, 1000);
            }
            if (scoreDisplay) scoreDisplay.textContent = score;

            selectedWord = null;
            selectedTranslation = null;

            if (pairsMade === originalWords.length && checkAnswersBtn) {
                checkAnswersBtn.click(); // Auto-check when all pairs are made
            }
        }
    }

    function checkAllAnswers() {
        if(gameFeedback) gameFeedback.textContent = `Игра окончена! Ваш результат: ${score} из ${originalWords.length}`;
        // Disable further interaction
        document.querySelectorAll('.match-item').forEach(item => {
            item.removeEventListener('click', handleItemClick);
            if (!item.classList.contains('paired')) { // Highlight unattempted or wrongly paired items if any logic added for that
                 item.style.cursor = 'default';
            }
        });
        if (checkAnswersBtn) checkAnswersBtn.disabled = true;
    }

    function resetGame() {
        selectedWord = null;
        selectedTranslation = null;
        score = 0;
        pairsMade = 0;

        // Re-shuffle
        random.shuffle(jumbledWords); // Need to implement shuffle if not available globally
        random.shuffle(jumbledTranslations); // Or re-fetch from server if preferred for true new shuffle

        populateColumns(); // Repopulate with potentially new shuffle
        if (checkAnswersBtn) checkAnswersBtn.disabled = false;
        if (gameFeedback) gameFeedback.textContent = "Игра сброшена. Попробуйте снова!";
    }

    // Simple shuffle function (Fisher-Yates) if not available globally
    // This should ideally be part of a utility library or a more robust setup
    const random = {
        shuffle: function(array) {
            let currentIndex = array.length,  randomIndex;
            while (currentIndex != 0) {
                randomIndex = Math.floor(Math.random() * currentIndex);
                currentIndex--;
                [array[currentIndex], array[randomIndex]] = [
                array[randomIndex], array[currentIndex]];
            }
            return array;
        }
    };


    // Initialization
    if (parseJsonData()) {
        if (originalWords.length > 0) {
            populateColumns();
            if (checkAnswersBtn) {
                checkAnswersBtn.addEventListener('click', checkAllAnswers);
            }
            if (resetGameBtn) {
                resetGameBtn.addEventListener('click', resetGame);
            }
        } else {
            if(gameFeedback) gameFeedback.textContent = "Нет слов для игры в этом модуле.";
            if (checkAnswersBtn) checkAnswersBtn.disabled = true;
            if (resetGameBtn) resetGameBtn.disabled = true;
        }
    }
});
