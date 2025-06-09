let questionCount = 1;

document.addEventListener('DOMContentLoaded', function() {
    // Добавляем первые варианты ответов
    addOption(0);
    addOption(0);

    // Обработчик добавления вопроса
    document.getElementById('add-question').addEventListener('click', function() {
        addQuestion();
    });

    // Обработчики для добавления вариантов
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('add-option')) {
            const questionBlock = e.target.closest('.question-block');
            const questionIndex = questionBlock.dataset.question;
            addOption(questionIndex);
        }
    });
});

function addQuestion() {
    const container = document.getElementById('questions-container');
    const questionDiv = document.createElement('div');
    questionDiv.className = 'question-block';
    questionDiv.dataset.question = questionCount;
    
    questionDiv.innerHTML = `
        <h5>Вопрос ${questionCount + 1}</h5>
        <div class="form-group">
            <label>Текст вопроса:</label>
            <input type="text" name="question_${questionCount}_text" class="form-control" required>
        </div>
        
        <div class="form-group">
            <label>Тип ответа:</label>
            <select name="question_${questionCount}_type" class="form-control">
                <option value="single">Один правильный ответ</option>
                <option value="multiple">Несколько правильных ответов</option>
            </select>
        </div>
        
        <div class="options-container">
        </div>
        
        <button type="button" class="btn btn-sm btn-secondary add-option">Добавить вариант</button>
        <hr>
    `;
    
    container.appendChild(questionDiv);
    
    // Добавляем два варианта по умолчанию
    addOption(questionCount);
    addOption(questionCount);
    
    questionCount++;
    document.getElementById('question-count').value = questionCount;
}

function addOption(questionIndex) {
    const questionBlock = document.querySelector(`[data-question="${questionIndex}"]`);
    const optionsContainer = questionBlock.querySelector('.options-container');
    const optionIndex = optionsContainer.children.length;
    
    const optionDiv = document.createElement('div');
    optionDiv.className = 'form-group row';
    optionDiv.innerHTML = `
        <div class="col-md-1">
            <input type="checkbox" name="question_${questionIndex}_option_${optionIndex}_correct" class="form-check-input">
        </div>
        <div class="col-md-11">
            <input type="text" name="question_${questionIndex}_option_${optionIndex}" class="form-control" placeholder="Вариант ответа">
        </div>
        <input type="hidden" name="question_${questionIndex}_option_count" value="${optionIndex + 1}">
    `;
    
    optionsContainer.appendChild(optionDiv);
}
