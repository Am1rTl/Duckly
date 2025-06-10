document.addEventListener('DOMContentLoaded', function() {
    const classSelect = document.getElementById('class_number');
    const unitSelectMain = document.getElementById('unit_select_main');
    const moduleSelectMain = document.getElementById('module_select_main');
    const addModuleToTestBtn = document.getElementById('add_module_to_test_btn');
    const selectedModulesListDiv = document.getElementById('selected_modules_list');
    const form = document.querySelector('form');

    const testTypeSelect = document.getElementById('test_type');
    const dictationOptionsGroup = document.getElementById('dictation_options_group');
    const dictationWordSourceRadios = document.querySelectorAll('input[name="dictation_word_source"]');
    const randomWordCountGroup = document.getElementById('dictation_random_word_count_group');
    const specificWordsGroup = document.getElementById('dictation_specific_words_group');
    const specificWordsCheckboxContainer = document.getElementById('specific_words_checkbox_container');

    const wordSourceTypeSelect = document.getElementById('word_source_type');
    const moduleSelectionArea = document.getElementById('module_selection_area_container');
    const customWordsArea = document.getElementById('custom_words_area_container');
    const addLetterModeContainer = document.getElementById('add_letter_mode_container');
    const customWordPairsContainer = document.getElementById('custom_word_pairs_container');

    function updateUnitOptions(units) {
        unitSelectMain.innerHTML = '<option value="">Выберите юнит</option>';
        units.forEach(unit => {
            unitSelectMain.innerHTML += `<option value="${unit}">${unit}</option>`;
        });
        unitSelectMain.disabled = units.length === 0;
        moduleSelectMain.innerHTML = '<option value="">Сначала выберите юнит</option>';
        moduleSelectMain.disabled = true;
    }

    function updateModuleOptions(modules) {
        moduleSelectMain.innerHTML = '<option value="">Выберите модуль</option>';
        modules.forEach(module => {
            moduleSelectMain.innerHTML += `<option value="${module}">${module}</option>`;
        });
        moduleSelectMain.disabled = modules.length === 0;
    }

    if (classSelect) {
        classSelect.addEventListener('change', function() {
            const classValue = this.value;
            if (classValue) {
                fetch(`/get_units_for_class?class_name=${classValue}`)
                    .then(response => response.json()).then(updateUnitOptions);
            } else {
                updateUnitOptions([]);
            }
            selectedModulesListDiv.innerHTML = '<p><em>Модули не выбраны.</em></p>';
            document.querySelectorAll('input[name="modules[]"]').forEach(inp => inp.remove());
            if (testTypeSelect.value === 'dictation') fetchWordsForSpecificSelection();
        });
    }

    if (unitSelectMain) {
        unitSelectMain.addEventListener('change', function() {
            const classValue = classSelect.value;
            const unitValue = this.value;
            if (unitValue && classValue) {
                fetch(`/get_modules_for_unit?class_name=${classValue}&unit_name=${unitValue}`)
                    .then(response => response.json()).then(updateModuleOptions);
            } else {
                updateModuleOptions([]);
            }
        });
    }

    let selectedModulesForTest = [];

    if (addModuleToTestBtn) {
        addModuleToTestBtn.addEventListener('click', function() {
            const classVal = classSelect.value;
            const unitVal = unitSelectMain.value;
            const moduleVal = moduleSelectMain.value;

            if (classVal && unitVal && moduleVal) {
                const moduleIdentifier = `${classVal}|${unitVal}|${moduleVal}`;
                if (!selectedModulesForTest.includes(moduleIdentifier)) {
                    selectedModulesForTest.push(moduleIdentifier);

                    const hiddenInput = document.createElement('input');
                    hiddenInput.type = 'hidden';
                    hiddenInput.name = 'modules[]';
                    hiddenInput.value = moduleIdentifier;
                    hiddenInput.id = `hidden-module-${moduleIdentifier.replace(/[^a-zA-Z0-9]/g, '-')}`;
                    if (form) form.appendChild(hiddenInput);

                    if (selectedModulesListDiv.querySelector('p')) {
                        selectedModulesListDiv.innerHTML = '';
                    }
                    const itemDiv = document.createElement('div');
                    itemDiv.classList.add('module-item-display');
                    itemDiv.textContent = `${classVal} класс - ${unitVal} - ${moduleVal}`;
                    itemDiv.dataset.identifier = moduleIdentifier;

                    const removeBtn = document.createElement('button');
                    removeBtn.innerHTML = '<i class="fas fa-times"></i>';
                    removeBtn.type = 'button';
                    removeBtn.classList.add('btn', 'btn-danger', 'btn-sm', 'remove-module-btn'); // Added 'remove-module-btn' for potential delegation
                    removeBtn.style.marginLeft = '10px';
                    removeBtn.style.cursor = 'pointer';
                    // Event listener for this specific button
                    removeBtn.addEventListener('click', function() {
                        selectedModulesForTest = selectedModulesForTest.filter(id => id !== moduleIdentifier);
                        const hiddenInputToRemove = document.getElementById(`hidden-module-${moduleIdentifier.replace(/[^a-zA-Z0-9]/g, '-')}`);
                        if (hiddenInputToRemove) hiddenInputToRemove.remove();
                        itemDiv.remove();
                        if (selectedModulesForTest.length === 0) {
                            selectedModulesListDiv.innerHTML = '<p><em>Модули не выбраны.</em></p>';
                        }
                        if (testTypeSelect.value === 'dictation') fetchWordsForSpecificSelection();
                    });
                    itemDiv.appendChild(removeBtn);
                    selectedModulesListDiv.appendChild(itemDiv);
                    if (testTypeSelect.value === 'dictation') fetchWordsForSpecificSelection();
                } else {
                    alert('Этот модуль уже добавлен.');
                }
            } else {
                alert('Пожалуйста, выберите класс, юнит и модуль.');
            }
        });
    }

    if (wordSourceTypeSelect) {
        wordSourceTypeSelect.addEventListener('change', function() {
            const involvesModules = (this.value === 'modules_only' || this.value === 'modules_and_custom');
            const involvesCustom = (this.value === 'custom_only' || this.value === 'modules_and_custom');

            if(moduleSelectionArea) moduleSelectionArea.style.display = involvesModules ? 'block' : 'none';
            if(customWordsArea) customWordsArea.style.display = involvesCustom ? 'block' : 'none';

            toggleDictationOptions();
        });
    }

    // Обновленная функция для показа соответствующих полей
    function updateFormFields() {
        const testType = testTypeSelect.value;
        const testDirectionGroup = document.getElementById('test-direction-group');
        const textContentGroup = document.getElementById('text-content-group');

        // Получаем элементы для управления видимостью
        const sourcesAndWordSettingsAccordionItem = document.getElementById('headingTwo')?.closest('.accordion-item'); // id="headingTwo" is inside the item
        const textContentMetaFormContainer = document.getElementById('text_content_meta_form_container');
        const textQuestionManagementContainer = document.getElementById('text_question_management_container');
        const specificSettingsCollapse = document.getElementById('collapseThree');
        const specificSettingsButton = document.querySelector('button[data-bs-target="#collapseThree"]');

        // Скрываем все дополнительные поля по умолчанию
        if (testDirectionGroup) testDirectionGroup.style.display = 'none';
        if (textContentGroup) textContentGroup.style.display = 'none';
        if (textContentMetaFormContainer) textContentMetaFormContainer.style.display = 'none';
        if (textQuestionManagementContainer) textQuestionManagementContainer.style.display = 'none';

        // Показываем/скрываем "Источники и настойка слов"
        if (sourcesAndWordSettingsAccordionItem) {
            sourcesAndWordSettingsAccordionItem.style.display = (testType === 'text_based') ? 'none' : 'block';
        }

        // Скрываем все описания
        document.querySelectorAll('.test-description').forEach(desc => {
            desc.style.display = 'none';
        });

        // Показываем соответствующее описание
        const descElement = document.getElementById(`desc-${testType}`);
        if (descElement) {
            descElement.style.display = 'block';
        }

        // Логика для разных типов тестов
        if (testType === 'multiple_choice' || testType === 'multiple_choice_multiple' ||
            testType === 'word_translation_choice' || testType === 'translation_word_choice') {
            if (testDirectionGroup) testDirectionGroup.style.display = 'block';
        } else if (testType === 'text_based') {
            if (textContentGroup) textContentGroup.style.display = 'block'; // Это старое поле для текста, возможно, его тоже надо будет скрыть или использовать
            if (textContentMetaFormContainer) textContentMetaFormContainer.style.display = 'block';
            if (textQuestionManagementContainer) textQuestionManagementContainer.style.display = 'block';

            // Расширяем аккордеон "Специфичные настройки типа теста"
            if (specificSettingsCollapse && !specificSettingsCollapse.classList.contains('show')) {
                specificSettingsCollapse.classList.add('show');
            }
            if (specificSettingsButton) {
                specificSettingsButton.setAttribute('aria-expanded', 'true');
                specificSettingsButton.classList.remove('collapsed');
            }
        } else {
             // Если выбран другой тип теста, убедимся, что специфичные настройки свернуты, если они не должны быть активны
            if (specificSettingsCollapse && specificSettingsCollapse.classList.contains('show') && testType !== 'text_based') {
                // Это условие может потребовать доработки, если другие типы тестов тоже используют collapseThree
                // Пока оставляем так, чтобы свернуть, если это не text_based
                // specificSettingsCollapse.classList.remove('show');
                // if (specificSettingsButton) {
                //     specificSettingsButton.setAttribute('aria-expanded', 'false');
                //     specificSettingsButton.classList.add('collapsed');
                // }
            }
        }
        
        updateOtherFields(testType); // Эта функция уже есть и обрабатывает moduleSelectionGroup и customWordsGroup
    }
    
    function updateOtherFields(testType) {
        const moduleSelectionGroup = document.getElementById('module_selection_area_container'); // Это контейнер для выбора модулей из Источников
        const customWordsGroup = document.getElementById('custom_words_area_container'); // Это контейнер для кастомных слов из Источников
        
        // Для 'text_based' эти группы не нужны, так как "Источники и настойка слов" целиком скрывается.
        // Но если бы они были вне того аккордеона, их тоже надо было бы скрывать.
        // Логика ниже была для скрытия этих полей, если они *не* в аккордеоне "Источники..."
        // Поскольку "Источники и настойка слов" скрывается целиком, эта дополнительная логика может быть избыточной
        // для moduleSelectionGroup и customWordsGroup, если они находятся ВНУТРИ #collapseTwo.
        // Однако, если они находятся в #collapseOne (Основные настройки), то эта логика все еще нужна.
        // Судя по всему, они являются частью "Источники и настройка слов", поэтому их видимость будет управляться
        // скрытием родительского accordion-item. Оставляем на случай, если структура HTML иная.

        if (testType === 'text_based') {
            // Если эти элементы не внутри collapseTwo, их нужно скрыть отдельно.
            // Но так как collapseTwo скрывается, то и они скроются.
            // Эта проверка здесь на всякий случай, если они внезапно окажутся в другом месте.
            if (moduleSelectionGroup && moduleSelectionGroup.closest('#collapseTwo') === null) {
                 moduleSelectionGroup.style.display = 'none';
            }
            if (customWordsGroup && customWordsGroup.closest('#collapseTwo') === null) {
                 customWordsGroup.style.display = 'none';
            }
        } else {
            // Для других типов тестов, которые используют модули/кастомные слова, убедимся, что они видны.
            // Это актуально, если они не являются частью аккордеона "Источники...", либо если тот аккордеон видим.
            // Дополнительно нужно проверить wordSourceTypeSelect, как это делается в toggleDictationOptions
            const wordSourceType = wordSourceTypeSelect ? wordSourceTypeSelect.value : null;
            const involvesModules = (wordSourceType === 'modules_only' || wordSourceType === 'modules_and_custom');
            const involvesCustom = (wordSourceType === 'custom_only' || wordSourceType === 'modules_and_custom');

            if (moduleSelectionGroup && moduleSelectionGroup.closest('#collapseTwo') === null) {
                 moduleSelectionGroup.style.display = involvesModules ? 'block' : 'none';
            }
            if (customWordsGroup && customWordsGroup.closest('#collapseTwo') === null) {
                 customWordsGroup.style.display = involvesCustom ? 'block' : 'none';
            }
        }
    }

    if (testTypeSelect) {
        testTypeSelect.addEventListener('change', function() {
            if(addLetterModeContainer) addLetterModeContainer.style.display = this.value === 'add_letter' ? 'block' : 'none';
            // toggleDictationOptions(); // toggleDictationOptions теперь вызывается из updateFormFields или wordSourceTypeSelect.change
            updateFormFields();
        });
    }

    function toggleDictationOptions() {
        if (!testTypeSelect || !wordSourceTypeSelect || !dictationOptionsGroup) return;

        const isDictation = testTypeSelect.value === 'dictation';
        // Проверяем, видима ли секция "Источники и настройка слов"
        const sourcesAccordionItem = document.getElementById('headingTwo')?.closest('.accordion-item');
        const sourcesVisible = sourcesAccordionItem ? sourcesAccordionItem.style.display !== 'none' : true;

        // Опции диктанта показываем только если это диктант И видна секция источников
        if (isDictation && sourcesVisible) {
            dictationOptionsGroup.style.display = 'block';
            // Дополнительно, нужно проверить wordSourceTypeSelect для показа moduleSelectionArea и customWordsArea
            const wordSourceType = wordSourceTypeSelect.value;
            const involvesModules = (wordSourceType === 'modules_only' || wordSourceType === 'modules_and_custom');
            const involvesCustom = (wordSourceType === 'custom_only' || wordSourceType === 'modules_and_custom');

            if(moduleSelectionArea) moduleSelectionArea.style.display = involvesModules ? 'block' : 'none';
            if(customWordsArea) customWordsArea.style.display = involvesCustom ? 'block' : 'none';

            updateDictationSubOptions();
        } else {
            dictationOptionsGroup.style.display = 'none';
            if(randomWordCountGroup) randomWordCountGroup.style.display = 'none';
            if(specificWordsGroup) specificWordsGroup.style.display = 'none';
            // Также скроем moduleSelectionArea и customWordsArea если они не для диктанта или источники скрыты
            if(moduleSelectionArea) moduleSelectionArea.style.display = 'none';
            if(customWordsArea) customWordsArea.style.display = 'none';
        }
    }

    // ... (остальной код toggleDictationOptions и updateDictationSubOptions)

    // Внутри DOMContentLoaded, после инициализации всех элементов:
    // ...

    if (wordSourceTypeSelect) {
        wordSourceTypeSelect.addEventListener('change', function() {
            // const involvesModules = (this.value === 'modules_only' || this.value === 'modules_and_custom');
            // const involvesCustom = (this.value === 'custom_only' || this.value === 'modules_and_custom');

            // if(moduleSelectionArea) moduleSelectionArea.style.display = involvesModules ? 'block' : 'none';
            // if(customWordsArea) customWordsArea.style.display = involvesCustom ? 'block' : 'none';
            // Эта логика теперь часть toggleDictationOptions, чтобы учесть видимость родительского аккордеона
            toggleDictationOptions();
        });
    }

    function toggleDictationOptions() {
        if (!testTypeSelect || !wordSourceTypeSelect || !dictationOptionsGroup) return; // Guard clause

        const isDictation = testTypeSelect.value === 'dictation';
        const usesModules = wordSourceTypeSelect.value === 'modules_only' || wordSourceTypeSelect.value === 'modules_and_custom';

        if (isDictation && usesModules) {
            dictationOptionsGroup.style.display = 'block';
            updateDictationSubOptions();
        } else {
            dictationOptionsGroup.style.display = 'none';
            if(randomWordCountGroup) randomWordCountGroup.style.display = 'none';
            if(specificWordsGroup) specificWordsGroup.style.display = 'none';
        }
    }

    function updateDictationSubOptions() {
        let selectedSourceRadio = document.querySelector('input[name="dictation_word_source"]:checked');
        if (!selectedSourceRadio) return; // Guard if no radio is checked
        let selectedSource = selectedSourceRadio.value;

        if(randomWordCountGroup) randomWordCountGroup.style.display = (selectedSource === 'random_from_module') ? 'block' : 'none';
        if(specificWordsGroup) {
            specificWordsGroup.style.display = (selectedSource === 'selected_specific') ? 'block' : 'none';
            if (selectedSource === 'selected_specific') fetchWordsForSpecificSelection();
        }
    }

    if (dictationWordSourceRadios) {
        dictationWordSourceRadios.forEach(radio => radio.addEventListener('change', updateDictationSubOptions));
    }

    function fetchWordsForSpecificSelection() {
        if (!specificWordsCheckboxContainer) return;

        const currentSelectedModuleIdentifiers = Array.from(document.querySelectorAll('input[name="modules[]"]')).map(cb => cb.value);
        specificWordsCheckboxContainer.innerHTML = '<p>Загрузка слов...</p>';

        const selectedDictationSource = document.querySelector('input[name="dictation_word_source"]:checked');

        if (currentSelectedModuleIdentifiers.length === 0 && selectedDictationSource && selectedDictationSource.value === 'selected_specific') {
            specificWordsCheckboxContainer.innerHTML = '<p>Сначала добавьте модули в тест выше, чтобы увидеть слова для выбора.</p>'; return;
        }

        if (currentSelectedModuleIdentifiers.length > 0) {
            fetch(`/get_words_for_module_selection?modules=${currentSelectedModuleIdentifiers.join(',')}`)
            .then(response => response.json())
            .then(data => {
                specificWordsCheckboxContainer.innerHTML = '';
                if (data.words && data.words.length > 0) {
                    data.words.forEach(word => {
                        const div = document.createElement('div'); div.classList.add('form-check');
                        const checkbox = document.createElement('input');
                        checkbox.type = 'checkbox'; checkbox.name = 'dictation_specific_word_ids[]';
                        checkbox.value = word.id; checkbox.id = 'dict_word_sel_' + word.id;
                        checkbox.classList.add('form-check-input');
                        const label = document.createElement('label');
                        label.htmlFor = 'dict_word_sel_' + word.id; label.textContent = word.text;
                        label.classList.add('form-check-label');
                        label.style.fontWeight = 'normal';
                        div.appendChild(checkbox); div.appendChild(label);
                        specificWordsCheckboxContainer.appendChild(div);
                    });
                } else { specificWordsCheckboxContainer.innerHTML = '<p>Нет слов в выбранных модулях.</p>'; }
            })
            .catch(error => { console.error('Error fetching words for dictation:', error); specificWordsCheckboxContainer.innerHTML = '<p>Ошибка при загрузке слов.</p>'; });
        } else if (selectedDictationSource && selectedDictationSource.value === 'selected_specific') {
             specificWordsCheckboxContainer.innerHTML = '<p>Сначала добавьте модули в тест выше.</p>';
        } else {
            specificWordsCheckboxContainer.innerHTML = ''; // Clear if not applicable
        }
    }

    // Привязываем обработчик события
    if (testTypeSelect) {
        testTypeSelect.addEventListener('change', updateFormFields);
        // Вызываем при загрузке страницы для правильной инициализации
        updateFormFields();
    }
    
    // Валидация для text_based тестов
    if (form) {
        form.addEventListener('submit', function(e) {
            const testType = testTypeSelect.value;
            const textContent = document.getElementById('text_content');
            
            if (testType === 'text_based' && (!textContent.value || textContent.value.trim().length < 50)) {
                e.preventDefault();
                alert('Для теста по тексту необходимо загрузить текст длиной не менее 50 символов.');
                textContent.focus();
                return false;
            }
        });
    }

    // Initial state setup
    toggleDictationOptions();
    if (wordSourceTypeSelect) wordSourceTypeSelect.dispatchEvent(new Event('change'));
    if (testTypeSelect) testTypeSelect.dispatchEvent(new Event('change'));

    const addCustomWordPairBtn = document.getElementById('add_custom_word_pair_btn');
    if (addCustomWordPairBtn && customWordPairsContainer) {
        addCustomWordPairBtn.addEventListener('click', function() {
            const newPair = document.createElement('div');
            newPair.classList.add('custom-word-pair');
            newPair.innerHTML = `
                <input type="text" name="custom_words[]" placeholder="Слово" class="form-control">
                <input type="text" name="custom_translations[]" placeholder="Перевод" class="form-control">
                <button type="button" class="btn-remove-custom-word btn btn-danger btn-sm"><i class="fas fa-times"></i></button>
            `; // Changed class for remove button and removed inline onclick
            customWordPairsContainer.appendChild(newPair);
        });

        // Event delegation for removing custom word pairs
        customWordPairsContainer.addEventListener('click', function(event) {
            if (event.target.closest('.btn-remove-custom-word')) {
                event.target.closest('.custom-word-pair').remove();
            }
        });
    }

    // --- START: Logic for Text-Based Test Question Management ---
    let currentTextQuestions = [];

    const textQAddBtn = document.getElementById('add_text_question_btn_in_test'); // Ensure this ID is on the button in HTML
    const currentTextQuestionsList = document.getElementById('current_text_questions_list');
    const textQuestionsJsonInput = document.getElementById('text_questions_json');

    const textQType = document.getElementById('text_q_type');
    const textQText = document.getElementById('text_q_text');
    const textQOption1 = document.getElementById('text_q_option1');
    const textQOption2 = document.getElementById('text_q_option2');
    const textQOption3 = document.getElementById('text_q_option3');
    const textQOption4 = document.getElementById('text_q_option4');
    const textQOptions = [textQOption1, textQOption2, textQOption3, textQOption4]; // Array for easier access

    const textQCorrectAnswerHiddenInput = document.getElementById('text_q_correct_answer_hidden_input'); // The UI helper hidden input
    const textQPoints = document.getElementById('text_q_points');

    const textQOptionsContainer = document.getElementById('text_q_optionsContainer');
    const textQCorrectAnswerSelector = document.getElementById('text_q_correctAnswerSelector');
    const textQAnswerOptionsPreview = document.getElementById('text_q_answerOptionsPreview');
    const textQMultipleCorrectAnswerSelector = document.getElementById('text_q_multipleCorrectAnswerSelector');
    const textQMultipleAnswerOptionsPreview = document.getElementById('text_q_multipleAnswerOptionsPreview');
    const textQTrueFalseSelector = document.getElementById('text_q_trueFalseSelector');
    const textQOpenAnswerInputContainer = document.getElementById('text_q_openAnswerInput'); // The div container
    const textQOpenAnswerText = document.getElementById('text_q_open_answer_text'); // The actual input field

    function updateTextQuestionsJsonInput() {
        if (textQuestionsJsonInput) {
            textQuestionsJsonInput.value = JSON.stringify(currentTextQuestions);
        }
    }

    function renderCurrentTextQuestions() {
        if (!currentTextQuestionsList) return;
        currentTextQuestionsList.innerHTML = ''; // Clear previous

        if (currentTextQuestions.length === 0) {
            currentTextQuestionsList.innerHTML = '<p><em>Вопросы, добавленные к этому тексту, появятся здесь.</em></p>';
            return;
        }

        currentTextQuestions.forEach((q, index) => {
            const itemDiv = document.createElement('div');
            itemDiv.classList.add('module-item-display', 'mb-2'); // Using similar styling
            itemDiv.style.padding = '10px';
            itemDiv.style.border = '1px solid #eee';
            itemDiv.style.borderRadius = '5px';

            let optionsDisplay = '';
            if (q.options && q.options.length > 0) {
                optionsDisplay = `<ul>${q.options.map(opt => `<li>${opt}</li>`).join('')}</ul>`;
            }

            let correctAnswerDisplay = Array.isArray(q.correct_answer) ? q.correct_answer.join(', ') : q.correct_answer;

            itemDiv.innerHTML = `
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <strong>Вопрос ${index + 1}:</strong> ${q.question_text} <br>
                        <small class="text-muted">Тип: ${q.question_type}, Баллы: ${q.points}</small>
                        ${optionsDisplay ? `<small class="text-muted d-block">Варианты:</small>${optionsDisplay}` : ''}
                        <small class="text-muted d-block">Правильный ответ: ${correctAnswerDisplay}</small>
                    </div>
                    <button type="button" class="btn btn-danger btn-sm remove-text-q-btn" data-question-index="${index}">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
            currentTextQuestionsList.appendChild(itemDiv);
        });
    }

    function clearTextQuestionForm() {
        if(textQType) textQType.value = '';
        if(textQText) textQText.value = '';
        textQOptions.forEach(opt => { if(opt) opt.value = ''; });
        if(textQCorrectAnswerHiddenInput) textQCorrectAnswerHiddenInput.value = '';
        if(textQPoints) textQPoints.value = '1';
        if(textQOpenAnswerText) textQOpenAnswerText.value = '';

        // Reset UI elements for answer selection
        if(textQAnswerOptionsPreview) textQAnswerOptionsPreview.innerHTML = '<p class="text-muted">Заполните варианты</p>';
        if(textQMultipleAnswerOptionsPreview) textQMultipleAnswerOptionsPreview.innerHTML = '<p class="text-muted">Заполните варианты</p>';
        document.querySelectorAll('#text_q_trueFalseSelector .tf-option-btn.selected').forEach(btn => btn.classList.remove('selected'));

        if(textQType) textQToggleOptionsLogic(); // Trigger visibility update
    }

    function handleAddTextQuestion() {
        if (!textQType || !textQText || !textQCorrectAnswerHiddenInput || !textQPoints) return;

        const questionType = textQType.value;
        const questionText = textQText.value.trim();
        let correctAnswer = textQCorrectAnswerHiddenInput.value.trim();
        const points = parseInt(textQPoints.value, 10) || 1;
        let options = [];

        if (!questionType) { alert('Пожалуйста, выберите тип вопроса.'); return; }
        if (!questionText) { alert('Пожалуйста, введите текст вопроса.'); textQText.focus(); return; }

        if (questionType === 'multiple_choice' || questionType === 'multiple_select') {
            options = textQOptions.map(opt => opt.value.trim()).filter(opt => opt !== '');
            if (options.length < 2) {
                alert('Для вопросов с выбором ответа необходимо как минимум 2 варианта.');
                if(textQOption1) textQOption1.focus();
                return;
            }
            if (!correctAnswer) {
                alert('Пожалуйста, укажите правильный ответ для вопроса с выбором.'); return;
            }
            if (questionType === 'multiple_select') {
                try {
                    const parsedAnswer = JSON.parse(correctAnswer);
                    if (!Array.isArray(parsedAnswer) || parsedAnswer.length === 0) {
                        alert('Для множественного выбора правильный ответ должен быть непустым списком.'); return;
                    }
                    correctAnswer = parsedAnswer; // Keep as array
                } catch (e) {
                    alert('Ошибка в формате правильного ответа для множественного выбора.'); return;
                }
            }
        } else if (questionType === 'true_false') {
            if (!correctAnswer) { alert('Пожалуйста, выберите правильный ответ (Да/Нет/Не указано).'); return; }
        } else if (questionType === 'open_answer') {
            if (!correctAnswer) { alert('Пожалуйста, введите правильный ответ для открытого вопроса.'); if(textQOpenAnswerText) textQOpenAnswerText.focus(); return; }
        }

        currentTextQuestions.push({
            question_type: questionType,
            question_text: questionText,
            options: options,
            correct_answer: correctAnswer,
            points: points
        });

        updateTextQuestionsJsonInput();
        renderCurrentTextQuestions();
        clearTextQuestionForm();
    }

    function updateTextQAnswerOptionsPreviewLogic() {
        if (!textQAnswerOptionsPreview || !textQCorrectAnswerHiddenInput) return;
        textQAnswerOptionsPreview.innerHTML = '';
        let hasOptions = false;
        textQOptions.forEach(input => {
            const value = input.value.trim();
            if (value) {
                hasOptions = true;
                const optionBtn = document.createElement('button');
                optionBtn.type = 'button';
                optionBtn.className = 'option-preview-btn btn btn-outline-secondary me-2 mb-2'; // Bootstrap classes
                optionBtn.textContent = value;
                optionBtn.dataset.value = value;
                if (textQCorrectAnswerHiddenInput.value === value) {
                    optionBtn.classList.add('selected', 'btn-primary');
                    optionBtn.classList.remove('btn-outline-secondary');
                }
                optionBtn.addEventListener('click', function() {
                    textQAnswerOptionsPreview.querySelectorAll('.option-preview-btn').forEach(btn => {
                        btn.classList.remove('selected', 'btn-primary');
                        btn.classList.add('btn-outline-secondary');
                    });
                    this.classList.add('selected', 'btn-primary');
                    this.classList.remove('btn-outline-secondary');
                    textQCorrectAnswerHiddenInput.value = value;
                });
                textQAnswerOptionsPreview.appendChild(optionBtn);
            }
        });
        if (!hasOptions) {
            textQAnswerOptionsPreview.innerHTML = '<p class="text-muted">Заполните варианты ответов выше, затем нажмите на правильный вариант.</p>';
        }
    }

    function updateTextQMultipleAnswerOptionsPreviewLogic() {
        if (!textQMultipleAnswerOptionsPreview || !textQCorrectAnswerHiddenInput) return;
        textQMultipleAnswerOptionsPreview.innerHTML = '';
        let currentSelectedValues = [];
        try {
            currentSelectedValues = JSON.parse(textQCorrectAnswerHiddenInput.value || '[]');
            if (!Array.isArray(currentSelectedValues)) currentSelectedValues = [];
        } catch (e) { currentSelectedValues = []; }

        let hasOptions = false;
        textQOptions.forEach(input => {
            const value = input.value.trim();
            if (value) {
                hasOptions = true;
                const optionBtn = document.createElement('button');
                optionBtn.type = 'button';
                optionBtn.className = 'multiple-option-btn btn btn-outline-secondary me-2 mb-2'; // Bootstrap classes
                optionBtn.textContent = value;
                optionBtn.dataset.value = value;

                if (currentSelectedValues.includes(value)) {
                    optionBtn.classList.add('selected', 'btn-primary');
                    optionBtn.classList.remove('btn-outline-secondary');
                }

                optionBtn.addEventListener('click', function() {
                    this.classList.toggle('selected');
                    this.classList.toggle('btn-primary');
                    this.classList.toggle('btn-outline-secondary');

                    const selectedValues = [];
                    textQMultipleAnswerOptionsPreview.querySelectorAll('.multiple-option-btn.selected').forEach(btn => {
                        selectedValues.push(btn.dataset.value);
                    });
                    textQCorrectAnswerHiddenInput.value = JSON.stringify(selectedValues);
                });
                textQMultipleAnswerOptionsPreview.appendChild(optionBtn);
            }
        });
         if (!hasOptions) {
            textQMultipleAnswerOptionsPreview.innerHTML = '<p class="text-muted">Заполните варианты ответов выше, затем выберите правильные.</p>';
        }
    }

    function textQToggleOptionsLogic() {
        if (!textQType) return;
        const questionType = textQType.value;

        if(textQOptionsContainer) textQOptionsContainer.style.display = 'none';
        if(textQCorrectAnswerSelector) textQCorrectAnswerSelector.style.display = 'none';
        if(textQMultipleCorrectAnswerSelector) textQMultipleCorrectAnswerSelector.style.display = 'none';
        if(textQTrueFalseSelector) textQTrueFalseSelector.style.display = 'none';
        if(textQOpenAnswerInputContainer) textQOpenAnswerInputContainer.style.display = 'none';

        if(textQCorrectAnswerHiddenInput) textQCorrectAnswerHiddenInput.value = ''; // Clear previous answer

        if (questionType === 'multiple_choice') {
            if(textQOptionsContainer) textQOptionsContainer.style.display = 'block';
            if(textQCorrectAnswerSelector) textQCorrectAnswerSelector.style.display = 'block';
            updateTextQAnswerOptionsPreviewLogic();
        } else if (questionType === 'multiple_select') {
            if(textQOptionsContainer) textQOptionsContainer.style.display = 'block';
            if(textQMultipleCorrectAnswerSelector) textQMultipleCorrectAnswerSelector.style.display = 'block';
            updateTextQMultipleAnswerOptionsPreviewLogic();
        } else if (questionType === 'true_false') {
            if(textQTrueFalseSelector) textQTrueFalseSelector.style.display = 'block';
        } else if (questionType === 'open_answer') {
            if(textQOpenAnswerInputContainer) textQOpenAnswerInputContainer.style.display = 'block';
        }
    }

    if (textQAddBtn) {
        textQAddBtn.addEventListener('click', handleAddTextQuestion);
    }

    if (currentTextQuestionsList) {
        currentTextQuestionsList.addEventListener('click', function(event) {
            const removeButton = event.target.closest('.remove-text-q-btn');
            if (removeButton) {
                const indexToRemove = parseInt(removeButton.dataset.questionIndex, 10);
                if (!isNaN(indexToRemove) && indexToRemove >= 0 && indexToRemove < currentTextQuestions.length) {
                    currentTextQuestions.splice(indexToRemove, 1);
                    updateTextQuestionsJsonInput();
                    renderCurrentTextQuestions();
                }
            }
        });
    }

    if (textQType) {
        textQType.addEventListener('change', textQToggleOptionsLogic);
    }

    textQOptions.forEach(optInput => {
        if(optInput) optInput.addEventListener('input', function() {
            if(textQType && textQType.value === 'multiple_choice') updateTextQAnswerOptionsPreviewLogic();
            if(textQType && textQType.value === 'multiple_select') updateTextQMultipleAnswerOptionsPreviewLogic();
        });
    });

    if (textQTrueFalseSelector) {
        textQTrueFalseSelector.querySelectorAll('.tf-option-btn').forEach(button => {
            button.addEventListener('click', function() {
                if(!textQCorrectAnswerHiddenInput) return;
                textQTrueFalseSelector.querySelectorAll('.tf-option-btn').forEach(btn => {
                    btn.classList.remove('selected', 'btn-success', 'btn-danger', 'btn-warning'); // Assuming Bootstrap for selected state
                    if(btn.dataset.value === "Да") btn.classList.add('btn-outline-success');
                    else if(btn.dataset.value === "Нет") btn.classList.add('btn-outline-danger');
                    else btn.classList.add('btn-outline-warning');
                });
                this.classList.add('selected');
                if(this.dataset.value === "Да") {this.classList.remove('btn-outline-success'); this.classList.add('btn-success');}
                else if(this.dataset.value === "Нет") {this.classList.remove('btn-outline-danger'); this.classList.add('btn-danger');}
                else {this.classList.remove('btn-outline-warning'); this.classList.add('btn-warning');}
                textQCorrectAnswerHiddenInput.value = this.dataset.value;
            });
        });
    }

    if (textQOpenAnswerText) {
        textQOpenAnswerText.addEventListener('input', function() {
            if(textQCorrectAnswerHiddenInput) textQCorrectAnswerHiddenInput.value = this.value.trim();
        });
    }

    // Ensure JSON input is updated before form submission
    if (form) {
        form.addEventListener('submit', function() {
            if (testTypeSelect && testTypeSelect.value === 'text_based') {
                updateTextQuestionsJsonInput(); // Make sure it's up-to-date
            }
        });
    }

    // Initial calls for text question UI if text_based is selected by default (though unlikely for new test)
    if (testTypeSelect && testTypeSelect.value === 'text_based') {
        textQToggleOptionsLogic();
        renderCurrentTextQuestions();
    } else { // Default state for question form when not text_based (or on page load before type selection)
        if(textQType) textQToggleOptionsLogic(); // Set up based on empty/default type
        if(currentTextQuestionsList) currentTextQuestionsList.innerHTML = '<p><em>Вопросы добавляются, если выбран тип теста "Тест по тексту".</em></p>';
    }
    // --- END: Logic for Text-Based Test Question Management ---

});
