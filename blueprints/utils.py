from flask import session, redirect, url_for, flash
from models import db, User, Word
import random
from datetime import datetime

def get_current_user():
    """Safely retrieves the current user using SQLAlchemy's modern API."""
    if 'user_id' not in session:
        return None
    return db.session.get(User, session['user_id'])

def require_login(f):
    """Decorator to check if a user is logged in."""
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def require_teacher(f):
    """Decorator to check if the user is a teacher."""
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user or user.teacher != 'yes':
            flash('Access denied. Teacher privileges required.', 'error')
            return redirect(url_for('tests.hello'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def generate_options_with_fallback(target_word, selected_modules, class_number, mode='word_to_translation'):
    """
    Generates 4 answer options with a fallback mechanism for multiple-choice tests.
    """
    correct_answer = target_word.perevod if mode == 'word_to_translation' else target_word.word
    
    same_module_words = Word.query.filter_by(
        classs=target_word.classs,
        unit=target_word.unit,
        module=target_word.module
    ).filter(Word.id != target_word.id).all()
    
    wrong_options = []
    
    if same_module_words:
        options_from_module = [w.perevod if mode == 'word_to_translation' else w.word 
                             for w in same_module_words]
        wrong_options.extend(random.sample(options_from_module, 
                                         min(3, len(options_from_module))))
    
    if len(wrong_options) < 3:
        same_unit_words = Word.query.filter_by(
            classs=target_word.classs,
            unit=target_word.unit
        ).filter(
            Word.id != target_word.id,
            Word.module != target_word.module
        ).all()
        
        if same_unit_words:
            options_from_unit = [w.perevod if mode == 'word_to_translation' else w.word 
                               for w in same_unit_words]
            needed = 3 - len(wrong_options)
            wrong_options.extend(random.sample(options_from_unit, 
                                             min(needed, len(options_from_unit))))
    
    if len(wrong_options) < 3:
        other_class_words = Word.query.filter_by(classs=target_word.classs).filter(
            Word.id != target_word.id,
            Word.unit != target_word.unit
        ).all()
        
        if other_class_words:
            options_from_class = [w.perevod if mode == 'word_to_translation' else w.word 
                                for w in other_class_words]
            needed = 3 - len(wrong_options)
            wrong_options.extend(random.sample(options_from_class, 
                                             min(needed, len(options_from_class))))
    
    while len(wrong_options) < 3:
        wrong_options.append(f"Option {len(wrong_options) + 1}")
    
    all_options = wrong_options[:3] + [correct_answer]
    random.shuffle(all_options)
    
    return all_options

def format_time_taken(minutes):
    """
    Formats test completion time for display.
    """
    if minutes is None or minutes < 0:
        return "0 мин"
    
    if minutes == 0:
        return "<1 мин"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if hours == 0:
        return f"{remaining_minutes} мин"
    elif remaining_minutes == 0:
        return f"{hours} ч"
    else:
        return f"{hours} ч {remaining_minutes} мин"

def auto_clear_previous_test_results(teacher_user, class_number, new_test_id):
    """
    Automatically clears previous test results when a new test is created.
    """
    from models import Test, TestResult, TestAnswer, TextTestAnswer
    AUTO_CLEAR_RESULTS_ON_NEW_TEST = True
    CLEAR_ONLY_ACTIVE_TESTS = True
    
    if not AUTO_CLEAR_RESULTS_ON_NEW_TEST:
        return 0, []
    
    try:
        query = Test.query.filter(
            Test.created_by == teacher_user.id,
            Test.classs == class_number,
            Test.id != new_test_id
        )
        
        if CLEAR_ONLY_ACTIVE_TESTS:
            query = query.filter(Test.is_active == True)
        
        previous_tests = query.all()
        
        results_cleared_count = 0
        tests_affected = []
        
        for prev_test in previous_tests:
            results_to_delete = TestResult.query.filter_by(test_id=prev_test.id).all()
            
            if results_to_delete:
                tests_affected.append(prev_test.title)
                
                for result in results_to_delete:
                    TestAnswer.query.filter_by(test_result_id=result.id).delete(synchronize_session=False)
                    TextTestAnswer.query.filter_by(test_result_id=result.id).delete(synchronize_session=False)
                    db.session.delete(result)
                    results_cleared_count += 1
        
        if results_cleared_count > 0:
            db.session.commit()
        
        return results_cleared_count, tests_affected
        
    except Exception as e:
        db.session.rollback()
        print(f"Error during auto-clear of test results: {e}")
        raise e