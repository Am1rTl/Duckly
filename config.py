import os
from datetime import timedelta
import tempfile
from pathlib import Path

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a-default-development-secret-key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session configuration
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=15)
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'duckly_'
    SESSION_COOKIE_NAME = 'duckly_session'
    SESSION_COOKIE_SECURE = False  # Set True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_PATH = '/'

    # Auto-clear test results settings
    AUTO_CLEAR_RESULTS_ON_NEW_TEST = True
    CLEAR_ONLY_ACTIVE_TESTS = True

    # Define session file directory based on environment
    @property
    def SESSION_FILE_DIR(self):
        if os.path.exists('/app'):
            # In Docker, use a persistent directory
            session_dir = '/app/flask_session'
        else:
            # Locally use a directory in the project root
            session_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'sessions')
        
        # Ensure the directory exists and has proper permissions
        os.makedirs(session_dir, exist_ok=True, mode=0o750)
        return session_dir
        
    # Configure cache settings
    CACHE_TYPE = 'SimpleCache'  # Using in-memory cache instead of filesystem cache
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes

    # Define database path based on environment
    @property
    def SQLALCHEMY_DATABASE_URI(self):
        if os.path.exists('/app'):
            # Running in Docker
            return 'sqlite:////app/instance/app.db'
        else:
            # Local run
            # Ensure instance path exists first
            instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
            os.makedirs(instance_path, exist_ok=True)
            return f'sqlite:///{os.path.join(instance_path, "app.db")}'
