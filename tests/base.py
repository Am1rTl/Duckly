import unittest
import sys
import os

# Add the parent directory to the Python path to allow module imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import app and db from site_1.py (or your main application file)
from site_1 import app, db
from models import User, Word, Test, TestWord # Add other models as needed

class BaseTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Configure the app for testing ONCE for the test class
        app.config['TESTING'] = True
        # Use an in-memory SQLite database for tests
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        # Disable CSRF protection for tests if you use Flask-WTF
        app.config['WTF_CSRF_ENABLED'] = False
        # It's good practice to set a specific server name for tests
        app.config['SERVER_NAME'] = 'localhost.localdomain'
        # Ensure session configurations are suitable for testing if needed
        # For example, if SESSION_TYPE is 'filesystem', ensure it writes to a temp dir
        # app.config['SESSION_FILE_DIR'] = tempfile.mkdtemp() # If needed

        cls.app = app
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        db.create_all() # Create tables once per test class

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all() # Drop all tables once per test class
        cls.app_context.pop()

    def setUp(self):
        # Each test method will run within its own transaction, which we'll roll back
        self.client = self.app.test_client()
        db.session.begin_nested() # Start a nested transaction

        # Optional: Create a default user or other global test data for each test method
        self.create_test_user()

    def tearDown(self):
        db.session.rollback() # Rollback the nested transaction after each test

    def create_test_user(self, is_teacher=True, nick_suffix=""):
        # Helper to create a user and log them in
        # Ensure unique nick for multiple users in the same test class if needed
        nick = f"testuser{nick_suffix}"
        user = User.query.filter_by(nick=nick).first()
        if not user:
            user = User(
                fio=f"Test User {nick_suffix}",
                nick=nick,
                password="password123", # In a real app, hash this
                teacher="yes" if is_teacher else "no",
                class_number="5A" if not is_teacher else None # Default class for student
            )
            db.session.add(user)
            db.session.commit() # Commit to make user available for querying in tests

        # Simulate login by adding user_id to session
        with self.client.session_transaction() as sess:
            sess['user_id'] = user.id
            sess['user_nick'] = user.nick
            sess['user_role'] = 'teacher' if is_teacher else 'student'
        return user

    def create_teacher_user(self, nick_suffix=""):
        return self.create_test_user(is_teacher=True, nick_suffix=nick_suffix)

    def create_student_user(self, nick_suffix=""):
        return self.create_test_user(is_teacher=False, nick_suffix=nick_suffix)

if __name__ == '__main__':
    unittest.main()
