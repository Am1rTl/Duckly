from flask import Blueprint, render_template, redirect, url_for
from blueprints.utils import get_current_user, require_login

# Blueprint dedicated to user profile related functionality.
# In the future this blueprint will include additional features such as profile editing, password change,
# avatar upload, etc.
profile_bp = Blueprint('profile', __name__, url_prefix='/profile')

@profile_bp.route('/')
@require_login
def profile_page():
    """Show the current user's profile information."""
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))
    return render_template('profile.html', user=user, fio=user.fio or '', nick=user.nick or '')

@profile_bp.route('/edit')
@require_login
def edit_profile():
    """Placeholder for future profile editing functionality."""
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))
    return render_template('edit_profile.html', user=user)
