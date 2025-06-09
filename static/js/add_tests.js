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
        
        // Скрываем все дополнительные поля
        if (testDirectionGroup) testDirectionGroup.style.display = 'none';
        if (textContentGroup) textContentGroup.style.display = 'none';
        
        // Скрываем все описания
        document.querySelectorAll('.test-description').forEach(desc => {
            desc.style.display = 'none';
        });
        
        // Показываем соответствующее описание
        const descElement = document.getElementById(`desc-${testType}`);
        if (descElement) {
            descElement.style.display = 'block';
        }
        
        // Показываем направление теста для multiple choice
        if (testType === 'multiple_choice' || testType === 'multiple_choice_multiple' || 
            testType === 'word_translation_choice' || testType === 'translation_word_choice') {
            if (testDirectionGroup) testDirectionGroup.style.display = 'block';
        }
        
        // Показываем текстовое поле для text_based тестов
        if (testType === 'text_based') {
            if (textContentGroup) textContentGroup.style.display = 'block';
        }
        
        // Обновляем другие поля в зависимости от типа
        updateOtherFields(testType);
    }
    
    function updateOtherFields(testType) {
        // Скрываем/показываем поля модулей в зависимости от типа теста
        const moduleSelectionGroup = document.getElementById('module_selection_area_container');
        const customWordsGroup = document.getElementById('custom_words_area_container');
        
        if (testType === 'text_based') {
            // Для тестов по тексту не нужны модули и кастомные слова
            if (moduleSelectionGroup) moduleSelectionGroup.style.display = 'none';
            if (customWordsGroup) customWordsGroup.style.display = 'none';
        } else {
            // Для остальных типов показываем стандартные поля
            if (moduleSelectionGroup) moduleSelectionGroup.style.display = 'block';
            if (customWordsGroup) customWordsGroup.style.display = 'block';
        }
    }

    if (testTypeSelect) {
        testTypeSelect.addEventListener('change', function() {
            if(addLetterModeContainer) addLetterModeContainer.style.display = this.value === 'add_letter' ? 'block' : 'none';
            toggleDictationOptions();
            updateFormFields(); // Добавляем вызов новой функции
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
});
