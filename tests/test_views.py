import unittest
import json
from tests.base import BaseTestCase # Changed to absolute import
from models import db, User, Test, TestWord, Word # Import necessary models

class TestAppViews(BaseTestCase):

    def test_create_test_model_with_text_content(self):
        """Test creating a Test model instance with text_content."""
        u = User.query.filter_by(nick="testuser").first()
        if not u: # Should have been created by BaseTestCase.setUp -> create_test_user
            u = self.create_test_user(is_teacher=True)

        test = Test(
            title="Text Content Test",
            classs="5A",
            type="text_based",
            link="unique_link_text_content",
            created_by=u.id,
            text_content="This is the main text for the test.",
            word_order="sequential"  # Added missing non-nullable field
        )
        db.session.add(test)
        db.session.commit()

        retrieved_test = Test.query.filter_by(link="unique_link_text_content").first()
        self.assertIsNotNone(retrieved_test)
        self.assertEqual(retrieved_test.text_content, "This is the main text for the test.")
        self.assertEqual(retrieved_test.type, "text_based")

    def test_create_test_word_model_with_question_type(self):
        """Test creating a TestWord model instance with question_type."""
        u = User.query.filter_by(nick="testuser").first()
        test_obj = Test(
            title="Question Type Test",
            classs="6B",
            type="multiple_choice_multiple",
            link="q_type_test",
            created_by=u.id,
            word_order="random"  # Added missing non-nullable field
        )
        db.session.add(test_obj)
        db.session.commit()

        test_word = TestWord(
            test_id=test_obj.id,
            word="Which of these are colors?",
            options=json.dumps(["Red", "Blue", "Table", "Chair"]),
            correct_answer=json.dumps(["Red", "Blue"]),
            question_type="multiple", # New field
            word_order=1,
            perevod="Select all correct options."  # Added missing non-nullable field
        )
        db.session.add(test_word)
        db.session.commit()

        retrieved_word = TestWord.query.filter_by(word="Which of these are colors?").first()
        self.assertIsNotNone(retrieved_word)
        self.assertEqual(retrieved_word.question_type, "multiple")
        self.assertEqual(retrieved_word.test_id, test_obj.id)

    def test_create_text_based_test_route(self):
        """Test the /create_test route for a text_based test."""
        self.create_teacher_user(nick_suffix="_teacher_tb") # Ensure logged in as teacher

        response = self.client.post('/create_test', data={
            'title': 'My Text Based Test',
            'class_number': '7C',
            'test_type': 'text_based',
            'time_limit': '30',
            'word_order': 'sequential',
            'text_content': 'This is the detailed text for the text-based test.'
            # Add other required fields from your form if any
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200) # Assuming redirect to a page showing success

        test = Test.query.filter_by(title='My Text Based Test').first()
        self.assertIsNotNone(test)
        self.assertEqual(test.type, 'text_based')
        self.assertEqual(test.classs, '7C')
        self.assertEqual(test.text_content, 'This is the detailed text for the text-based test.')

    def test_create_multiple_choice_multiple_test_route(self):
        """Test the /create_test route for a multiple_choice_multiple test."""
        self.create_teacher_user(nick_suffix="_teacher_mcm")

        response = self.client.post('/create_test', data={
            'title': 'My Multi-Select Test',
            'class_number': '8D',
            'test_type': 'multiple_choice_multiple',
            'time_limit': '0', # Unlimited
            'word_order': 'random',
            'word_count': '10'
            # No text_content for this type
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)

        test = Test.query.filter_by(title='My Multi-Select Test').first()
        self.assertIsNotNone(test)
        self.assertEqual(test.type, 'multiple_choice_multiple')
        self.assertEqual(test.classs, '8D')
        self.assertIsNone(test.text_content) # Should be None

    def test_configure_text_questions_route_add_single_answer(self):
        """Test adding a single-answer question via /configure_text_questions."""
        teacher = self.create_teacher_user(nick_suffix="_teacher_config_single")

        # First, create a text_based test
        text_test = Test(
            title="Config Text Test Single",
            classs="9A",
            type="text_based",
            link="config_test_single",
            created_by=teacher.id,
            text_content="Some interesting text to ask questions about.",
            word_order="sequential"  # Added missing non-nullable field
        )
        db.session.add(text_test)
        db.session.commit()

        response = self.client.post(f'/configure_text_questions/{text_test.id}', data={
            'question_text': 'What is the capital of France?',
            'options[]': ['Paris', 'London', 'Berlin', 'Rome'],
            'correct_options[]': ['0'], # Index of 'Paris'
            'question_type': 'single'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200) # Should redirect back to the same page

        test_word = TestWord.query.filter_by(test_id=text_test.id).first()
        self.assertIsNotNone(test_word)
        self.assertEqual(test_word.word, 'What is the capital of France?')
        self.assertEqual(test_word.question_type, 'single')

        options = json.loads(test_word.options)
        correct_answer = json.loads(test_word.correct_answer)

        self.assertListEqual(options, ['Paris', 'London', 'Berlin', 'Rome'])
        self.assertListEqual(correct_answer, ['Paris'])

    def test_configure_text_questions_route_add_multiple_answer(self):
        """Test adding a multiple-answer question via /configure_text_questions."""
        teacher = self.create_teacher_user(nick_suffix="_teacher_config_multi")

        text_test_multi = Test(
            title="Config Text Test Multi",
            classs="9B",
            type="text_based",
            link="config_test_multi",
            created_by=teacher.id,
            text_content="Another piece of text.",
            word_order="sequential"  # Added missing non-nullable field
        )
        db.session.add(text_test_multi)
        db.session.commit()

        response = self.client.post(f'/configure_text_questions/{text_test_multi.id}', data={
            'question_text': 'Which of these are primary colors?',
            'options[]': ['Red', 'Green', 'Blue', 'Yellow', 'Purple'],
            'correct_options[]': ['0', '2', '3'], # Indices of Red, Blue, Yellow (assuming primary for light)
            'question_type': 'multiple'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)

        test_word = TestWord.query.filter_by(test_id=text_test_multi.id).first()
        self.assertIsNotNone(test_word)
        self.assertEqual(test_word.word, 'Which of these are primary colors?')
        self.assertEqual(test_word.question_type, 'multiple')

        options = json.loads(test_word.options)
        correct_answers = json.loads(test_word.correct_answer)

        self.assertListEqual(options, ['Red', 'Green', 'Blue', 'Yellow', 'Purple'])
        self.assertListEqual(sorted(correct_answers), sorted(['Red', 'Blue', 'Yellow']))

if __name__ == '__main__':
    unittest.main()
