from site_1 import app, db, Word, Test, User
import random

# Sample data
classes = ["5", "6", "7", "8", "9", "10", "11"]
units = {
    "5": ["Unit 1", "Unit 2", "Unit 3", "Unit 4"],
    "6": ["Unit 1", "Unit 2", "Unit 3", "Unit 4"],
    "7": ["Unit 1", "Unit 2", "Unit 3", "Unit 4"],
    "8": ["Unit 1", "Unit 2", "Unit 3", "Unit 4"],
    "9": ["Unit 1", "Unit 2", "Unit 3", "Unit 4"],
    "10": ["Unit 1", "Unit 2", "Unit 3", "Unit 4"],
    "11": ["Unit 1", "Unit 2", "Unit 3", "Unit 4"]
}
modules = {
    "Unit 1": ["Module 1", "Module 2", "Module 3"],
    "Unit 2": ["Module 1", "Module 2", "Module 3"],
    "Unit 3": ["Module 1", "Module 2", "Module 3"],
    "Unit 4": ["Module 1", "Module 2", "Module 3"]
}

# English words with Russian translations
words_data = [
    {"word": "apple", "perevod": "яблоко"},
    {"word": "book", "perevod": "книга"},
    {"word": "cat", "perevod": "кошка"},
    {"word": "dog", "perevod": "собака"},
    {"word": "elephant", "perevod": "слон"},
    {"word": "flower", "perevod": "цветок"},
    {"word": "garden", "perevod": "сад"},
    {"word": "house", "perevod": "дом"},
    {"word": "ice", "perevod": "лёд"},
    {"word": "jacket", "perevod": "куртка"},
    {"word": "king", "perevod": "король"},
    {"word": "lamp", "perevod": "лампа"},
    {"word": "mouse", "perevod": "мышь"},
    {"word": "notebook", "perevod": "тетрадь"},
    {"word": "orange", "perevod": "апельсин"},
    {"word": "pencil", "perevod": "карандаш"},
    {"word": "queen", "perevod": "королева"},
    {"word": "river", "perevod": "река"},
    {"word": "sun", "perevod": "солнце"},
    {"word": "table", "perevod": "стол"},
    {"word": "umbrella", "perevod": "зонт"},
    {"word": "violin", "perevod": "скрипка"},
    {"word": "window", "perevod": "окно"},
    {"word": "xylophone", "perevod": "ксилофон"},
    {"word": "yellow", "perevod": "жёлтый"},
    {"word": "zebra", "perevod": "зебра"},
    {"word": "school", "perevod": "школа"},
    {"word": "teacher", "perevod": "учитель"},
    {"word": "student", "perevod": "ученик"},
    {"word": "classroom", "perevod": "класс"},
    {"word": "lesson", "perevod": "урок"},
    {"word": "homework", "perevod": "домашнее задание"},
    {"word": "exam", "perevod": "экзамен"},
    {"word": "friend", "perevod": "друг"},
    {"word": "family", "perevod": "семья"},
    {"word": "mother", "perevod": "мать"},
    {"word": "father", "perevod": "отец"},
    {"word": "sister", "perevod": "сестра"},
    {"word": "brother", "perevod": "брат"},
    {"word": "computer", "perevod": "компьютер"}
]

# Test types
test_types = ["Vocabulary", "Grammar", "Reading", "Listening"]

def populate_database():
    # Clear existing data (optional)
    print("Clearing existing data...")
    db.session.query(Word).delete()
    db.session.query(Test).delete()
    db.session.commit()
    
    print("Populating database with sample data...")
    
    # Add words
    words_added = 0
    for class_name in classes:
        for unit_name in units[class_name]:
            for module_name in modules[unit_name]:
                # Add 3-5 random words to each module
                num_words = random.randint(3, 5)
                for _ in range(num_words):
                    # Select a random word from our list
                    word_data = random.choice(words_data)
                    
                    # Create a new Word instance
                    new_word = Word(
                        word=word_data["word"],
                        perevod=word_data["perevod"],
                        classs=class_name,
                        unit=unit_name,
                        module=module_name
                    )
                    
                    db.session.add(new_word)
                    words_added += 1
    
    # Add tests
    tests_added = 0
    for class_name in classes:
        for unit_name in units[class_name]:
            # Create a test for each unit
            test_type = random.choice(test_types)
            link = f"{class_name}_{unit_name.replace(' ', '_')}_{random.randint(1000, 9999)}"
            
            new_test = Test(
                classs=class_name,
                unit=unit_name,
                type=test_type,
                link=link
            )
            
            db.session.add(new_test)
            tests_added += 1
    
    # Commit all changes
    db.session.commit()
    
    print(f"Database populated successfully with {words_added} words and {tests_added} tests!")

# Add a sample user if needed
def add_sample_user():
    # Check if user already exists
    existing_user = User.query.filter_by(nick="teacher").first()
    if existing_user:
        print("Sample user 'teacher' already exists.")
        return
    
    # Create a new user
    new_user = User(
        fio="Sample Teacher",
        nick="teacher",
        password="password123",
        secret_key="samplekey123",
        teacher="Yes"
    )
    
    db.session.add(new_user)
    db.session.commit()
    print("Sample user 'teacher' added successfully!")

if __name__ == "__main__":
    with app.app_context():
        # Make sure all tables exist
        db.create_all()
        
        # Populate the database
        populate_database()
        
        # Add a sample user
        add_sample_user()
