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
            ('good afternoon', 'добрый день'),
            ('good evening', 'добрый вечер'),
            ('how are you', 'как дела'),
            ('fine, thank you', 'хорошо, спасибо')
        ],
        'Formal Greetings': [
            ('pleased to meet you', 'рад познакомиться'),
            ('how do you do', 'здравствуйте (формально)'),
            ('it\'s a pleasure', 'это удовольствие'),
            ('may I introduce', 'позвольте представить'),
            ('farewell', 'прощайте')
        ],
        'Informal Greetings': [
            ('hi', 'привет'),
            ('bye', 'пока'),
            ('see ya', 'увидимся'),
            ('what\'s up', 'как дела (сл.)'),
            ('long time no see', 'давно не виделись')
        ],
        'Cardinal Numbers': [
            ('one', 'один'), ('two', 'два'), ('three', 'три'), ('four', 'четыре'),
            ('five', 'пять'), ('ten', 'десять'), ('twenty', 'двадцать'), ('one hundred', 'сто')
        ],
        'Ordinal Numbers': [
            ('first', 'первый'), ('second', 'второй'), ('third', 'третий'),
            ('fourth', 'четвертый'), ('fifth', 'пятый'), ('tenth', 'десятый'),
            ('twentieth', 'двадцатый')
        ],
        'Fractions': [
            ('half', 'половина'), ('quarter', 'четверть'), ('one third', 'одна треть'),
            ('two thirds', 'две трети'), ('three quarters', 'три четверти')
        ],
        'Basic Colors': [
            ('red', 'красный'), ('blue', 'синий'), ('green', 'зеленый'),
            ('yellow', 'желтый'), ('black', 'черный'), ('white', 'белый'),
            ('orange', 'оранжевый'), ('purple', 'фиолетовый')
        ],
        'Shades': [
            ('light blue', 'светло-синий'), ('dark green', 'темно-зеленый'),
            ('bright red', 'ярко-красный'), ('pale yellow', 'бледно-желтый'),
            ('deep purple', 'темно-фиолетовый'), ('navy blue', 'темно-синий')
        ],
        'Color Combinations': [
            ('red and blue', 'красный и синий'), ('black and white', 'черный и белый'),
            ('green and yellow', 'зеленый и желтый'), ('blue and white', 'синий и белый'),
            ('red and green', 'красный и зеленый'), ('orange and black', 'оранжевый и черный')
        ],
        'Family Members': [
            ('mother', 'мать'), ('father', 'отец'), ('sister', 'сестра'),
            ('brother', 'брат'), ('grandmother', 'бабушка'), ('grandfather', 'дедушка'),
            ('aunt', 'тетя'), ('uncle', 'дядя'), ('cousin', 'двоюродный брат/сестра')
        ],
        'Relationships': [
            ('family', 'семья'), ('parents', 'родители'), ('children', 'дети'),
            ('relatives', 'родственники'), ('spouse', 'супруг/супруга'),
            ('niece', 'племянница'), ('nephew', 'племянник')
        ],
        'Family Activities': [
            ('cook dinner', 'готовить ужин'), ('clean the house', 'убирать дом'),
            ('play games', 'играть в игры'), ('read books', 'читать книги'),
            ('watch TV', 'смотреть телевизор'), ('go for a walk', 'гулять'),
            ('visit relatives', 'посещать родственников')
        ],
        'Pets': [
            ('dog', 'собака'), ('cat', 'кошка'), ('bird', 'птица'),
            ('fish', 'рыба'), ('hamster', 'хомяк'), ('guinea pig', 'морская свинка'),
            ('rabbit', 'кролик')
        ],
        'Wild Animals': [
            ('lion', 'лев'), ('tiger', 'тигр'), ('elephant', 'слон'),
            ('monkey', 'обезьяна'), ('giraffe', 'жираф'), ('zebra', 'зебра'),
            ('bear', 'медведь'), ('wolf', 'волк')
        ],
        'Farm Animals': [
            ('cow', 'корова'), ('pig', 'свинья'), ('sheep', 'овца'),
            ('chicken', 'курица'), ('horse', 'лошадь'), ('duck', 'утка'),
            ('goat', 'коза')
        ],
        'Fruits': [
            ('apple', 'яблоко'), ('banana', 'банан'), ('orange', 'апельсин'),
            ('grape', 'виноград'), ('strawberry', 'клубника'), ('blueberry', 'черника'),
            ('pineapple', 'ананас'), ('mango', 'манго')
        ],
        'Vegetables': [
            ('carrot', 'морковь'), ('potato', 'картофель'), ('tomato', 'помидор'),
            ('cucumber', 'огурец'), ('onion', 'лук'), ('broccoli', 'брокколи'),
            ('spinach', 'шпинат'), ('pepper', 'перец')
        ],
        'Meals': [
            ('breakfast', 'завтрак'), ('lunch', 'обед'), ('dinner', 'ужин'),
            ('snack', 'перекус'), ('dessert', 'десерт'), ('supper', 'ужин (поздний)'),
            ('brunch', 'поздний завтрак')
        ],
        'School Subjects': [
            ('math', 'математика'), ('science', 'наука'), ('history', 'история'),
            ('geography', 'география'), ('literature', 'литература'),
            ('art', 'искусство'), ('music', 'музыка'), ('physical education', 'физкультура')
        ],
        'School Supplies': [
            ('pencil', 'карандаш'), ('notebook', 'тетрадь'), ('book', 'книга'),
            ('ruler', 'линейка'), ('eraser', 'ластик'), ('backpack', 'рюкзак'),
            ('pen', 'ручка'), ('scissors', 'ножницы')
        ],
        'School Activities': [
            ('study', 'учиться'), ('read', 'читать'), ('write', 'писать'),
            ('draw', 'рисовать'), ('calculate', 'вычислять'), ('listen to', 'слушать'),
            ('speak', 'говорить'), ('discuss', 'обсуждать')
        ],
        'Weather Conditions': [
            ('sunny', 'солнечно'), ('rainy', 'дождливо'), ('cloudy', 'облачно'),
            ('windy', 'ветрено'), ('snowy', 'снежно'), ('stormy', 'штормовой'),
            ('foggy', 'туманно'), ('icy', 'гололедица')
        ],
        'Seasons': [
            ('spring', 'весна'), ('summer', 'лето'), ('autumn', 'осень'),
            ('winter', 'зима'), ('season', 'сезон')
        ],
        'Weather Forecast': [
            ('temperature', 'температура'), ('forecast', 'прогноз погоды'),
            ('degree Celsius', 'градус Цельсия'), ('weather report', 'сводка погоды'),
            ('climate change', 'изменение климата'), ('humidity', 'влажность')
        ],
        'Basic Clothes': [
            ('shirt', 'рубашка'), ('pants', 'брюки'), ('dress', 'платье'),
            ('jacket', 'куртка'), ('shoes', 'обувь'), ('skirt', 'юбка'),
            ('sweater', 'свитер'), ('socks', 'носки')
        ],
        'Accessories': [
            ('hat', 'шляпа'), ('scarf', 'шарф'), ('gloves', 'перчатки'),
            ('belt', 'ремень'), ('watch', 'часы'), ('glasses', 'очки'),
            ('jewelry', 'ювелирные изделия')
        ],
        'Fashion': [
            ('style', 'стиль'), ('trend', 'тренд'), ('design', 'дизайн'),
            ('brand', 'бренд'), ('collection', 'коллекция'), ('fashionable', 'модный'),
            ('outfit', 'наряд')
        ],
        'Team Sports': [
            ('football', 'футбол'), ('basketball', 'баскетбол'), ('volleyball', 'волейбол'),
            ('hockey', 'хоккей'), ('soccer', 'футбол (американский)') # Уточнение для американского футбола
        ],
        'Individual Sports': [
            ('running', 'бег'), ('swimming', 'плавание'), ('cycling', 'велоспорт'),
            ('tennis', 'теннис'), ('gymnastics', 'гимнастика')
        ],
        'Sports Equipment': [
            ('ball', 'мяч'), ('racket', 'ракетка'), ('helmet', 'шлем'),
            ('skates', 'коньки'), ('uniform', 'форма')
        ],
        'Musical Instruments': [
            ('guitar', 'гитара'), ('piano', 'пианино'), ('drums', 'барабаны'),
            ('violin', 'скрипка'), ('flute', 'флейта')
        ],
        'Music Genres': [
            ('pop', 'поп-музыка'), ('rock', 'рок-музыка'), ('jazz', 'джаз'),
            ('classical music', 'классическая музыка'), ('hip hop', 'хип-хоп')
        ],
        'Music Terms': [
            ('melody', 'мелодия'), ('rhythm', 'ритм'), ('harmony', 'гармония'),
            ('composer', 'композитор'), ('lyrics', 'текст песни')
        ],
        'Transportation': [
            ('car', 'машина'), ('bus', 'автобус'), ('train', 'поезд'),
            ('plane', 'самолет'), ('bicycle', 'велосипед'), ('ship', 'корабль')
        ],
        'Accommodation': [
            ('hotel', 'отель'), ('apartment', 'квартира'), ('hostel', 'хостел'),
            ('tent', 'палатка'), ('resort', 'курорт')
        ],
        'Tourism': [
            ('travel', 'путешествие'), ('tourist', 'турист'), ('sightseeing', 'осмотр достопримечательностей'),
            ('attraction', 'достопримечательность'), ('souvenir', 'сувенир')
        ],
        'City Places': [
            ('park', 'парк'), ('museum', 'музей'), ('library', 'библиотека'),
            ('restaurant', 'ресторан'), ('supermarket', 'супермаркет')
        ],
        'City Services': [
            ('police station', 'полицейский участок'), ('fire station', 'пожарная станция'),
            ('hospital', 'больница'), ('post office', 'почтовое отделение'),
            ('bank', 'банк')
        ],
        'City Life': [
            ('traffic', 'дорожное движение'), ('pedestrian', 'пешеход'),
            ('public transport', 'общественный транспорт'), ('commute', 'поездка на работу'),
            ('skyscraper', 'небоскреб')
        ],
        'Landscapes': [
            ('mountain', 'гора'), ('river', 'река'), ('lake', 'озеро'),
            ('forest', 'лес'), ('desert', 'пустыня'), ('beach', 'пляж')
        ],
        'Plants': [
            ('tree', 'дерево'), ('flower', 'цветок'), ('grass', 'трава'),
            ('bush', 'куст'), ('leaf', 'лист')
        ],
        'Natural Phenomena': [
            ('earthquake', 'землетрясение'), ('volcano', 'вулкан'), ('tsunami', 'цунами'),
            ('flood', 'наводнение'), ('drought', 'засуха'), ('lightning', 'молния')
        ],
        'Computers': [
            ('keyboard', 'клавиатура'), ('mouse', 'мышь'), ('screen', 'экран'),
            ('laptop', 'ноутбук'), ('desktop', 'настольный компьютер')
        ],
        'Internet': [
            ('website', 'веб-сайт'), ('email', 'электронная почта'), ('search engine', 'поисковая система'),
            ('social media', 'социальные сети'), ('online', 'онлайн')
        ],
        'Gadgets': [
            ('smartphone', 'смартфон'), ('tablet', 'планшет'), ('headphones', 'наушники'),
            ('smartwatch', 'умные часы'), ('drone', 'дрон')
        ],
        'Physics': [
            ('gravity', 'гравитация'), ('energy', 'энергия'), ('force', 'сила'),
            ('motion', 'движение'), ('electricity', 'электричество')
        ],
        'Chemistry': [
            ('atom', 'атом'), ('molecule', 'молекула'), ('element', 'элемент'),
            ('compound', 'соединение'), ('reaction', 'реакция')
        ],
        'Biology': [
            ('cell', 'клетка'), ('gene', 'ген'), ('organism', 'организм'),
            ('ecosystem', 'экосистема'), ('evolution', 'эволюция')
        ],
        'Solar System': [
            ('sun', 'солнце'), ('moon', 'луна'), ('planet', 'планета'),
            ('star', 'звезда'), ('galaxy', 'галактика')
        ],
        'Space Exploration': [
            ('astronaut', 'космонавт'), ('spaceship', 'космический корабль'),
            ('satellite', 'спутник'), ('telescope', 'телескоп'), ('universe', 'вселенная')
        ],
        'Astronomy': [
            ('constellation', 'созвездие'), ('observatory', 'обсерватория'),
            ('celestial body', 'небесное тело'), ('comet', 'комета'), ('meteor', 'метеор')
        ],
        'Ancient History': [
            ('pyramid', 'пирамида'), ('empire', 'империя'), ('pharaoh', 'фараон'),
            ('gladiator', 'гладиатор'), ('civilization', 'цивилизация')
        ],
        'Modern History': [
            ('revolution', 'революция'), ('world war', 'мировая война'), ('cold war', 'холодная война'),
            ('globalization', 'глобализация'), ('digital age', 'цифровая эпоха')
        ],
        'Historical Events': [
            ('discovery', 'открытие'), ('invention', 'изобретение'), ('treaty', 'договор'),
            ('battle', 'битва'), ('declaration', 'декларация')
        ],
        'Countries': [
            ('country', 'страна'), ('capital', 'столица'), ('continent', 'континент'),
            ('ocean', 'океан'), ('border', 'граница')
        ],
        'Capitals': [
            ('Moscow', 'Москва'), ('London', 'Лондон'), ('Paris', 'Париж'),
            ('Berlin', 'Берлин'), ('Tokyo', 'Токио')
        ],
        'Landmarks': [
            ('Eiffel Tower', 'Эйфелева башня'), ('Great Wall', 'Великая стена'),
            ('Pyramids of Giza', 'Пирамиды Гизы'), ('Colosseum', 'Колизей'),
            ('Statue of Liberty', 'Статуя Свободы')
        ],
        'Traditions': [
            ('tradition', 'традиция'), ('custom', 'обычай'), ('ritual', 'ритуал'),
            ('ceremony', 'церемония'), ('folklore', 'фольклор')
        ],
        'Customs': [
            ('greeting', 'приветствие'), ('farewell', 'прощание'), ('dining etiquette', 'столовый этикет'),
            ('social norms', 'социальные нормы'), ('taboo', 'табу')
        ],
        'Festivals': [
            ('festival', 'фестиваль'), ('holiday', 'праздник'), ('celebration', 'празднование'),
            ('parade', 'парад'), ('carnival', 'карнавал')
        ],
        'Genres': [
            ('novel', 'роман'), ('poem', 'стихотворение'), ('play', 'пьеса'),
            ('short story', 'короткий рассказ'), ('essay', 'эссе')
        ],
        'Authors': [
            ('writer', 'писатель'), ('poet', 'поэт'), ('dramatist', 'драматург'),
            ('novelist', 'романист'), ('biographer', 'биограф')
        ],
        'Literary Terms': [
            ('plot', 'сюжет'), ('character', 'персонаж'), ('theme', 'тема'),
            ('metaphor', 'метафора'), ('symbolism', 'символизм')
        ],
        'Art Forms': [
            ('painting', 'живопись'), ('sculpture', 'скульптура'), ('drawing', 'рисунок'),
            ('photography', 'фотография'), ('architecture', 'архитектура')
        ],
        'Artists': [
            ('painter', 'художник'), ('sculptor', 'скульптор'), ('photographer', 'фотограф'),
            ('architect', 'архитектор'), ('musician', 'музыкант')
        ],
        'Art History': [
            ('Renaissance', 'Возрождение'), ('Baroque', 'Барокко'), ('Impressionism', 'Импрессионизм'),
            ('Cubism', 'Кубизм'), ('Surrealism', 'Сюрреализм')
        ],
        'News': [
            ('headline', 'заголовок'), ('reporter', 'репортер'), ('article', 'статья'),
            ('broadcast', 'трансляция'), ('journalism', 'журналистика')
        ],
        'Entertainment': [
            ('movie', 'фильм'), ('music', 'музыка'), ('theater', 'театр'),
            ('concert', 'концерт'), ('game', 'игра')
        ],
        'Social Media': [
            ('post', 'пост'), ('like', 'лайк'), ('share', 'поделиться'),
            ('follower', 'подписчик'), ('hashtag', 'хештег')
        ],
        'Companies': [
            ('company', 'компания'), ('corporation', 'корпорация'), ('startup', 'стартап'),
            ('business', 'бизнес'), ('enterprise', 'предприятие')
        ],
        'Marketing': [
            ('advertisement', 'реклама'), ('brand', 'бренд'), ('customer', 'клиент'),
            ('sales', 'продажи'), ('promotion', 'продвижение')
        ],
        'Management': [
            ('manager', 'менеджер'), ('leadership', 'лидерство'), ('teamwork', 'командная работа'),
            ('strategy', 'стратегия'), ('project', 'проект')
        ],
        'Economics': [
            ('economy', 'экономика'), ('supply and demand', 'спрос и предложение'),
            ('inflation', 'инфляция'), ('recession', 'рецессия'), ('market', 'рынок')
        ],
        'Finance': [
            ('money', 'деньги'), ('bank', 'банк'), ('investment', 'инвестиция'),
            ('budget', 'бюджет'), ('stock market', 'фондовый рынок')
        ],
        'Trade': [
            ('export', 'экспорт'), ('import', 'импорт'), ('tariff', 'тариф'),
            ('global trade', 'мировая торговля'), ('agreement', 'соглашение')
        ],
        'Government': [
            ('government', 'правительство'), ('president', 'президент'), ('parliament', 'парламент'),
            ('democracy', 'демократия'), ('constitution', 'конституция')
        ],
        'Elections': [
            ('election', 'выборы'), ('vote', 'голосовать'), ('candidate', 'кандидат'),
            ('campaign', 'кампания'), ('ballot', 'избирательный бюллетень')
        ],
        'International Relations': [
            ('diplomacy', 'дипломатия'), ('treaty', 'договор'), ('alliance', 'альянс'),
            ('conflict', 'конфликт'), ('peace', 'мир')
        ],
        'Diseases': [
            ('disease', 'болезнь'), ('symptom', 'симптом'), ('infection', 'инфекция'),
            ('virus', 'вирус'), ('bacteria', 'бактерии')
        ],
        'Treatment': [
            ('medicine', 'лекарство'), ('therapy', 'терапия'), ('surgery', 'хирургия'),
            ('vaccine', 'вакцина'), ('diagnosis', 'диагноз')
        ],
        'Healthcare': [
            ('hospital', 'больница'), ('doctor', 'врач'), ('nurse', 'медсестра'),
            ('patient', 'пациент'), ('clinic', 'клиника')
        ],
        'Legal System': [
            ('law', 'закон'), ('court', 'суд'), ('judge', 'судья'),
            ('lawyer', 'адвокат'), ('justice', 'справедливость')
        ],
        'Rights': [
            ('right', 'право'), ('freedom', 'свобода'), ('equality', 'равенство'),
            ('human rights', 'права человека'), ('citizen', 'гражданин')
        ],
        'Crimes': [
            ('crime', 'преступление'), ('theft', 'кража'), ('murder', 'убийство'),
            ('fraud', 'мошенничество'), ('arrest', 'арест')
        ],
        'Education System': [
            ('school', 'школа'), ('university', 'университет'), ('curriculum', 'учебный план'),
            ('grade', 'оценка'), ('diploma', 'диплом')
        ],
        'Learning': [
            ('learn', 'учиться'), ('knowledge', 'знание'), ('skill', 'навык'),
            ('practice', 'практика'), ('understand', 'понимать')
        ],
        'Teaching': [
            ('teach', 'учить'), ('teacher', 'учитель'), ('lesson', 'урок'),
            ('classroom', 'классная комната'), ('pedagogy', 'педагогика')
        ],
        'Philosophical Concepts': [
            ('existence', 'существование'), ('truth', 'истина'), ('reality', 'реальность'),
            ('knowledge', 'знание'), ('morality', 'мораль')
        ],
        'Philosophers': [
            ('Plato', 'Платон'), ('Aristotle', 'Аристотель'), ('Kant', 'Кант'),
            ('Nietzsche', 'Ницше'), ('Socrates', 'Сократ')
        ],
        'Ethics': [
            ('ethics', 'этика'), ('virtue', 'добродетель'), ('justice', 'справедливость'),
            ('duty', 'долг'), ('conscience', 'совесть')
        ],
        'Mental Processes': [
            ('thought', 'мысль'), ('memory', 'память'), ('perception', 'восприятие'),
            ('emotion', 'эмоция'), ('cognition', 'познание')
        ],
        'Behavior': [
            ('behavior', 'поведение'), ('habit', 'привычка'), ('reaction', 'реакция'),
            ('instinct', 'инстинкт'), ('adaptation', 'адаптация')
        ],
        'Personality': [
            ('personality', 'личность'), ('trait', 'черта характера'), ('temperament', 'темперамент'),
            ('character', 'характер'), ('self-esteem', 'самооценка')
        ],
        'Society': [
            ('society', 'общество'), ('culture', 'культура'), ('community', 'сообщество'),
            ('institution', 'институт'), ('social norm', 'социальная норма')
        ],
        'Social Groups': [
            ('family', 'семья'), ('peer group', 'группа сверстников'), ('organization', 'организация'),
            ('class', 'класс (социальный)'), ('nation', 'нация')
        ],
        'Social Issues': [
            ('poverty', 'бедность'), ('inequality', 'неравенство'), ('crime', 'преступность'),
            ('discrimination', 'дискриминация'), ('unemployment', 'безработица')
        ]
    }

    with app.app_context():
        # Очистка существующих данных
        TestWord.query.delete()
        Test.query.delete()
        Word.query.delete()
        User.query.delete()
        db.session.commit() # Коммит для очистки

        # Создание тестового учителя
        hashed_teacher_password = generate_password_hash('teacher')
        teacher = User(
            fio='Тестовый Учитель',
            nick='teacher',
            password=hashed_teacher_password,
            teacher='yes'
        )
        db.session.add(teacher)
        db.session.commit()

        # Создание тестового студента
        hashed_student_password = generate_password_hash('student')
        student = User(
            fio='Тестовый Студент',
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
                        words_to_add = test_words[module]
                    else:
                        # Если модуля нет в словаре, используем базовые слова для предотвращения ошибок
                        print(f"Warning: Module '{module}' not found in test_words. Using 'Basic Greetings' words.")
                        words_to_add = test_words['Basic Greetings'] # Fallback
                    
                    for word_en, word_ru in words_to_add:
                        new_word = Word(
                            word=word_en,
                            perevod=word_ru,
                            classs=class_num,
                            unit=unit,
                            module=module
                        )
                        db.session.add(new_word)
        db.session.commit() # Коммит после добавления всех слов

        # Создание тестового теста
        # Убедимся, что тест создается для существующих слов
        # Выберем случайный существующий модуль для теста, чтобы показать разнообразие
        # или просто создадим для первого класса, как в оригинале.
        
        # Для примера, создадим тест для 5 класса, Unit 1: Travel, Transportation
        test_class = '5'
        test_unit = 'Unit 1: Travel'
        test_module = 'Transportation'

        times = str(time.time()).split(".")
        test_link = times[0]+times[1]
        
        test = Test(
            title=f'Тест по {test_module}',
            classs=test_class,
            unit=test_unit,
            module=test_module,
            type='dictation',
            link=test_link,
            created_by=teacher.id,
            is_active=True,
            word_order='random'
        )
        db.session.add(test)
        db.session.commit()

        # Добавление слов в тест из выбранного модуля
        words_for_test = Word.query.filter_by(
            classs=test_class,
            unit=test_unit,
            module=test_module
        ).all()

        if not words_for_test:
            print(f"Warning: No words found for test module '{test_module}'. Test will be empty.")

        for idx, word_obj in enumerate(words_for_test):
            test_word = TestWord(
                test_id=test.id,
                word=word_obj.word,
                perevod=word_obj.perevod,
                correct_answer=word_obj.word,
                word_order=idx
            )
            db.session.add(test_word)
        
        db.session.commit() # Сохранение всех изменений
        print("Test data has been successfully loaded into the database!")

if __name__ == "__main__":
    generate_test_data()
