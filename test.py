from site_1 import app, db, Word, User, Test, TestWord
from werkzeug.security import generate_password_hash
import random
import time

def generate_test_data():
    # Список классов (1-11)
    classes = [str(i) for i in range(1, 12)]
    
    # Список юнитов для каждого класса
    units = {
        '1': ['Unit 1: Greetings', 'Unit 2: Numbers', 'Unit 3: Colors'],
        '2': ['Unit 1: Family', 'Unit 2: Animals', 'Unit 3: Food'],
        '3': ['Unit 1: School', 'Unit 2: Weather', 'Unit 3: Clothes'],
        '4': ['Unit 1: Hobbies', 'Unit 2: Sports', 'Unit 3: Music'],
        '5': ['Unit 1: Travel', 'Unit 2: City', 'Unit 3: Nature'],
        '6': ['Unit 1: Technology', 'Unit 2: Science', 'Unit 3: Space'],
        '7': ['Unit 1: History', 'Unit 2: Geography', 'Unit 3: Culture'],
        '8': ['Unit 1: Literature', 'Unit 2: Art', 'Unit 3: Media'],
        '9': ['Unit 1: Business', 'Unit 2: Economy', 'Unit 3: Politics'],
        '10': ['Unit 1: Medicine', 'Unit 2: Law', 'Unit 3: Education'],
        '11': ['Unit 1: Philosophy', 'Unit 2: Psychology', 'Unit 3: Sociology']
    }
    
    # Список модулей для каждого юнита
    modules = {
        'Unit 1: Greetings': ['Basic Greetings', 'Formal Greetings', 'Informal Greetings'],
        'Unit 2: Numbers': ['Cardinal Numbers', 'Ordinal Numbers', 'Fractions'],
        'Unit 3: Colors': ['Basic Colors', 'Shades', 'Color Combinations'],
        'Unit 1: Family': ['Family Members', 'Relationships', 'Family Activities'],
        'Unit 2: Animals': ['Pets', 'Wild Animals', 'Farm Animals'],
        'Unit 3: Food': ['Fruits', 'Vegetables', 'Meals'],
        'Unit 1: School': ['School Subjects', 'School Supplies', 'School Activities'],
        'Unit 2: Weather': ['Weather Conditions', 'Seasons', 'Weather Forecast'],
        'Unit 3: Clothes': ['Basic Clothes', 'Accessories', 'Fashion'],
        'Unit 1: Hobbies': ['Sports', 'Arts', 'Collecting'],
        'Unit 2: Sports': ['Team Sports', 'Individual Sports', 'Sports Equipment'],
        'Unit 3: Music': ['Musical Instruments', 'Music Genres', 'Music Terms'],
        'Unit 1: Travel': ['Transportation', 'Accommodation', 'Tourism'],
        'Unit 2: City': ['City Places', 'City Services', 'City Life'],
        'Unit 3: Nature': ['Landscapes', 'Plants', 'Natural Phenomena'],
        'Unit 1: Technology': ['Computers', 'Internet', 'Gadgets'],
        'Unit 2: Science': ['Physics', 'Chemistry', 'Biology'],
        'Unit 3: Space': ['Solar System', 'Space Exploration', 'Astronomy'],
        'Unit 1: History': ['Ancient History', 'Modern History', 'Historical Events'],
        'Unit 2: Geography': ['Countries', 'Capitals', 'Landmarks'],
        'Unit 3: Culture': ['Traditions', 'Customs', 'Festivals'],
        'Unit 1: Literature': ['Genres', 'Authors', 'Literary Terms'],
        'Unit 2: Art': ['Art Forms', 'Artists', 'Art History'],
        'Unit 3: Media': ['News', 'Entertainment', 'Social Media'],
        'Unit 1: Business': ['Companies', 'Marketing', 'Management'],
        'Unit 2: Economy': ['Economics', 'Finance', 'Trade'],
        'Unit 3: Politics': ['Government', 'Elections', 'International Relations'],
        'Unit 1: Medicine': ['Diseases', 'Treatment', 'Healthcare'],
        'Unit 2: Law': ['Legal System', 'Rights', 'Crimes'],
        'Unit 3: Education': ['Education System', 'Learning', 'Teaching'],
        'Unit 1: Philosophy': ['Philosophical Concepts', 'Philosophers', 'Ethics'],
        'Unit 2: Psychology': ['Mental Processes', 'Behavior', 'Personality'],
        'Unit 3: Sociology': ['Society', 'Social Groups', 'Social Issues']
    }
    
    # Словарь с тестовыми словами для каждого модуля
    test_words = {
        'Basic Greetings': [
            ('hello', 'привет'),
            ('goodbye', 'до свидания'),
            ('good morning', 'доброе утро'),
            ('good evening', 'добрый вечер'),
            ('how are you', 'как дела')
        ],
        'Formal Greetings': [
            ('good day', 'добрый день'),
            ('pleased to meet you', 'рад познакомиться'),
            ('welcome', 'добро пожаловать'),
            ('farewell', 'прощание'),
            ('best regards', 'с наилучшими пожеланиями')
        ],
        'Informal Greetings': [
            ('hi', 'привет'),
            ('bye', 'пока'),
            ('see you', 'увидимся'),
            ('take care', 'береги себя'),
            ('what\'s up', 'как дела')
        ],
        'Cardinal Numbers': [
            ('one', 'один'),
            ('two', 'два'),
            ('three', 'три'),
            ('four', 'четыре'),
            ('five', 'пять')
        ],
        'Ordinal Numbers': [
            ('first', 'первый'),
            ('second', 'второй'),
            ('third', 'третий'),
            ('fourth', 'четвертый'),
            ('fifth', 'пятый')
        ],
        'Fractions': [
            ('half', 'половина'),
            ('quarter', 'четверть'),
            ('third', 'треть'),
            ('two thirds', 'две трети'),
            ('three quarters', 'три четверти')
        ],
        'Basic Colors': [
            ('red', 'красный'),
            ('blue', 'синий'),
            ('green', 'зеленый'),
            ('yellow', 'желтый'),
            ('black', 'черный')
        ],
        'Shades': [
            ('light', 'светлый'),
            ('dark', 'темный'),
            ('bright', 'яркий'),
            ('pale', 'бледный'),
            ('deep', 'глубокий')
        ],
        'Color Combinations': [
            ('red and blue', 'красный и синий'),
            ('black and white', 'черный и белый'),
            ('green and yellow', 'зеленый и желтый'),
            ('blue and white', 'синий и белый'),
            ('red and green', 'красный и зеленый')
        ],
        'Family Members': [
            ('mother', 'мама'),
            ('father', 'папа'),
            ('sister', 'сестра'),
            ('brother', 'брат'),
            ('grandmother', 'бабушка')
        ],
        'Relationships': [
            ('family', 'семья'),
            ('parents', 'родители'),
            ('children', 'дети'),
            ('relatives', 'родственники'),
            ('cousin', 'двоюродный брат/сестра')
        ],
        'Family Activities': [
            ('cook', 'готовить'),
            ('clean', 'убирать'),
            ('play', 'играть'),
            ('read', 'читать'),
            ('watch', 'смотреть')
        ],
        'Pets': [
            ('dog', 'собака'),
            ('cat', 'кошка'),
            ('bird', 'птица'),
            ('fish', 'рыба'),
            ('hamster', 'хомяк')
        ],
        'Wild Animals': [
            ('lion', 'лев'),
            ('tiger', 'тигр'),
            ('elephant', 'слон'),
            ('monkey', 'обезьяна'),
            ('giraffe', 'жираф')
        ],
        'Farm Animals': [
            ('cow', 'корова'),
            ('pig', 'свинья'),
            ('sheep', 'овца'),
            ('chicken', 'курица'),
            ('horse', 'лошадь')
        ],
        'Fruits': [
            ('apple', 'яблоко'),
            ('banana', 'банан'),
            ('orange', 'апельсин'),
            ('grape', 'виноград'),
            ('strawberry', 'клубника')
        ],
        'Vegetables': [
            ('carrot', 'морковь'),
            ('potato', 'картофель'),
            ('tomato', 'помидор'),
            ('cucumber', 'огурец'),
            ('onion', 'лук')
        ],
        'Meals': [
            ('breakfast', 'завтрак'),
            ('lunch', 'обед'),
            ('dinner', 'ужин'),
            ('snack', 'перекус'),
            ('dessert', 'десерт')
        ],
        'School Subjects': [
            ('math', 'математика'),
            ('science', 'наука'),
            ('history', 'история'),
            ('geography', 'география'),
            ('literature', 'литература')
        ],
        'School Supplies': [
            ('pencil', 'карандаш'),
            ('notebook', 'тетрадь'),
            ('book', 'книга'),
            ('ruler', 'линейка'),
            ('eraser', 'ластик')
        ],
        'School Activities': [
            ('study', 'учиться'),
            ('read', 'читать'),
            ('write', 'писать'),
            ('draw', 'рисовать'),
            ('calculate', 'вычислять')
        ],
        'Weather Conditions': [
            ('sunny', 'солнечно'),
            ('rainy', 'дождливо'),
            ('cloudy', 'облачно'),
            ('windy', 'ветрено'),
            ('snowy', 'снежно')
        ],
        'Seasons': [
            ('spring', 'весна'),
            ('summer', 'лето'),
            ('autumn', 'осень'),
            ('winter', 'зима'),
            ('season', 'сезон')
        ],
        'Weather Forecast': [
            ('temperature', 'температура'),
            ('forecast', 'прогноз'),
            ('degree', 'градус'),
            ('weather', 'погода'),
            ('climate', 'климат')
        ],
        'Basic Clothes': [
            ('shirt', 'рубашка'),
            ('pants', 'брюки'),
            ('dress', 'платье'),
            ('jacket', 'куртка'),
            ('shoes', 'обувь')
        ],
        'Accessories': [
            ('hat', 'шляпа'),
            ('scarf', 'шарф'),
            ('gloves', 'перчатки'),
            ('belt', 'ремень'),
            ('watch', 'часы')
        ],
        'Fashion': [
            ('style', 'стиль'),
            ('trend', 'тренд'),
            ('design', 'дизайн'),
            ('brand', 'бренд'),
            ('collection', 'коллекция')
        ]
    }

    with app.app_context():
        # Очистка существующих данных
        TestWord.query.delete()
        Test.query.delete()
        Word.query.delete()
        User.query.delete()
        
        # Создание тестового учителя
        hashed_teacher_password = generate_password_hash('teacher')
        teacher = User(
            fio='Test Teacher',
            nick='teacher',
            password=hashed_teacher_password,
            teacher='yes'
        )
        db.session.add(teacher)
        db.session.commit()

        # Создание тестового студента
        hashed_student_password = generate_password_hash('student')
        student = User(
            fio='Test Student',
            nick='student',
            password=hashed_student_password,
            teacher='no',
            class_number='1'
        )
        db.session.add(student)
        db.session.commit()

        # Добавление слов в базу данных
        for class_num in classes:
            for unit in units[class_num]:
                for module in modules[unit]:
                    # Используем слова из словаря test_words
                    if module in test_words:
                        words = test_words[module]
                    else:
                        # Если модуля нет в словаре, используем слова из похожего модуля
                        similar_module = next((m for m in test_words.keys() if m.lower() in module.lower() or module.lower() in m.lower()), None)
                        if similar_module:
                            words = test_words[similar_module]
                        else:
                            # Если похожего модуля нет, используем базовые слова
                            words = test_words['Basic Greetings']
                    
                    for word, translation in words:
                        new_word = Word(
                            word=word,
                            perevod=translation,
                            classs=class_num,
                            unit=unit,
                            module=module
                        )
                        db.session.add(new_word)
        
        # Создание тестового теста
        times = str(time.time()).split(".")
        test_link = times[0]+times[1]
        
        test = Test(
            title='Test Greetings',
            classs='1',
            unit='Unit 1: Greetings',
            module='Basic Greetings',
            type='dictation',
            link=test_link,
            created_by=teacher.id,
            is_active=True,
            word_order='random'
        )
        db.session.add(test)
        db.session.commit()

        # Добавление слов в тест
        words = Word.query.filter_by(
            classs='1',
            unit='Unit 1: Greetings',
            module='Basic Greetings'
        ).all()

        for idx, word in enumerate(words):
            test_word = TestWord(
                test_id=test.id,
                word=word.word,
                perevod=word.perevod,
                correct_answer=word.word,
                word_order=idx
            )
            db.session.add(test_word)
        
        # Сохранение всех изменений
        db.session.commit()

if __name__ == "__main__":
    generate_test_data()
    print("Test data has been successfully loaded into the database!") 