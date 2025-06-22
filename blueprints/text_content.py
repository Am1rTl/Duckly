from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash
from models import db, TextContent, TextQuestion
from blueprints.utils import get_current_user, require_login, require_teacher
from datetime import datetime
import json

text_content_bp = Blueprint('text_content', __name__)

@text_content_bp.route('/add', methods=['GET', 'POST'])
@require_login
@require_teacher
def add_text_content():
    user = get_current_user()
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        class_number = request.form.get('class_number')
        unit = request.form.get('unit')
        module = request.form.get('module')
        
        if not title or not content or not class_number:
            flash('Please fill in all required fields.', 'error')
            return render_template('add_text_content.html', classes=[str(i) for i in range(1, 12)])
        
        text_content = TextContent(
            title=title,
            content=content,
            classs=class_number,
            unit=unit,
            module=module,
            created_by=user.id,
            created_at=datetime.utcnow()
        )
        db.session.add(text_content)
        try:
            db.session.commit()
            flash('Text content created successfully! Now add questions.', 'success')
            return redirect(url_for('text_content.add_questions', text_content_id=text_content.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating text content: {str(e)}', 'error')
            return render_template('add_text_content.html', classes=[str(i) for i in range(1, 12)])

    return render_template('add_text_content.html', classes=[str(i) for i in range(1, 12)])

# Root alias for listing text contents
@text_content_bp.route('/')
@require_login
def text_contents():
    return redirect(url_for('text_content.list_text_content'))

@text_content_bp.route('/list')
@require_login
def list_text_content():
    user = get_current_user()
    if user.teacher == 'yes':
        texts = TextContent.query.filter_by(created_by=user.id).order_by(TextContent.created_at.desc()).all()
    else:
        texts = TextContent.query.filter_by(classs=user.class_number).order_by(TextContent.created_at.desc()).all()
    
    return render_template('text_contents.html', contents=texts, is_teacher=user.teacher == 'yes')

@text_content_bp.route('/<int:text_content_id>/questions', methods=['GET', 'POST'])
@require_login
@require_teacher
def add_questions(text_content_id):
    text_content = db.session.get(TextContent, text_content_id)
    if not text_content:
        flash('Text content not found.', 'error')
        return redirect(url_for('text_content.list_text_content'))
    
    if text_content.created_by != get_current_user().id:
        flash('Access denied.', 'error')
        return redirect(url_for('text_content.list_text_content'))

    if request.method == 'POST':
        questions_data = request.form.get('questions_data')
        try:
            questions = json.loads(questions_data) if questions_data else []
            for idx, q in enumerate(questions):
                question = TextQuestion(
                    text_content_id=text_content.id,
                    question=q.get('question', ''),
                    question_type=q.get('type', 'open_answer'),
                    correct_answer=json.dumps(q.get('correct', []), ensure_ascii=False),
                    options=json.dumps(q.get('options', []), ensure_ascii=False),
                    points=q.get('points', 1),
                    order_number=idx
                )
                db.session.add(question)
            db.session.commit()
            flash('Questions added successfully!', 'success')
            return redirect(url_for('text_content.list_text_content'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving questions: {str(e)}', 'error')

    existing_questions = TextQuestion.query.filter_by(text_content_id=text_content.id).order_by(TextQuestion.order_number).all()
    questions_for_js = [
        {
            'question': q.question,
            'type': q.question_type,
            'correct': json.loads(q.correct_answer) if q.correct_answer else [],
            'options': json.loads(q.options) if q.options else [],
            'points': q.points
        } for q in existing_questions
    ]
    
    return render_template('add_text_questions.html',
                          text_content=text_content,
                          questions_for_js=json.dumps(questions_for_js, ensure_ascii=False))

@text_content_bp.route('/<int:text_content_id>')
@require_login
def view_text_content(text_content_id):
    text_content = db.session.get(TextContent, text_content_id)
    if not text_content:
        flash('Text content not found.', 'error')
        return redirect(url_for('text_content.list_text_content'))
    
    user = get_current_user()
    if user.teacher != 'yes' and text_content.classs != user.class_number:
        flash('Access denied.', 'error')
        return redirect(url_for('text_content.list_text_content'))

    questions = TextQuestion.query.filter_by(text_content_id=text_content.id).order_by(TextQuestion.order_number).all()
    return render_template('view_text_content.html',
                          text_content=text_content,
                          questions=questions,
                          is_teacher=user.teacher == 'yes')