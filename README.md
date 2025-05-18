# Duckly Educational Platform

This project is a web-based educational platform, likely designed for language learning, built with Python and Flask. It allows users to register, manage vocabulary (words), create various types of tests, take tests, and view results. The application is designed to be run in a Docker container.

## Features

*   **User Management:**
    *   User registration (students and teachers).
    *   User login and logout.
    *   User profiles.
*   **Vocabulary Management:**
    *   Adding, editing, and deleting words.
    *   Organizing words by class, unit, and module.
*   **Test Management (for Teachers):**
    *   Creating various types of tests:
        *   Dictation
        *   Add Letter (fill in missing letters)
        *   True/False
        *   Multiple Choice (single and multiple correct answers)
        *   Fill Word (fill in the blank)
    *   Setting test parameters like time limits, word order (random/sequential), and word count.
    *   Linking tests to specific classes, units, or modules.
    *   Archiving tests.
*   **Test Taking (for Students):**
    *   Taking available tests via a unique link.
    *   Submitting answers.
*   **Results Tracking:**
    *   Viewing test scores, correct/incorrect answers, and time taken.
*   **Quizlet-like Functionality:**
    *   Viewing words as flashcards for a given module.
*   **API Endpoints:**
    *   JSON endpoints for retrieving words, units, and modules, likely for dynamic frontend updates.

## Project Structure

```
.
├── .git/               # Git repository files
├── instance/           # Potentially for instance-specific configurations or data (e.g., persistent DB)
├── static/             # Static assets (CSS, JavaScript, images)
├── templates/          # HTML templates for the web interface
├── __pycache__/        # Python bytecode cache
├── app.db              # SQLite database file (Note: May be recreated on container start)
├── create_db.py        # Script to initialize the database schema
├── Dockerfile          # Defines the Docker image for the application
├── requirements.txt    # Python package dependencies
├── site_1.py           # Main Flask application file containing routes and logic
├── start.sh            # Script to build and run the Docker container
└── test.py             # Contains application tests
```

## Technical Stack

*   **Backend:** Python, Flask
*   **Database:** SQLite (via Flask-SQLAlchemy)
*   **Templating:** Jinja2
*   **Containerization:** Docker

## Setup and Installation

The application is designed to be run using Docker.

### Prerequisites

*   Docker installed and running.

### Running the Application

1.  **Clone the repository (if applicable):**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Build and Run with `start.sh`:**
    The provided `start.sh` script automates the build and run process:
    ```bash
    sh start.sh
    ```
    This script will:
    *   Build a Docker image named `duckly-app`.
    *   Remove any existing container named `duckly-container`.
    *   Run a new container named `duckly-container` in detached mode.
    *   Map port 1800 of the host to port 1800 of the container.
    *   Mount the local `./instance` directory to `/app/instance` in the container. (Note: the script currently uses an absolute path `/home/amir/Duckly/instance` for the volume, you might need to adjust this to your local path or `./instance`).

3.  **Access the application:**
    Once the container is running, the application should be accessible at `http://localhost:1800`.

### Database Initialization

The `Dockerfile` is currently configured to remove `app.db` every time the container starts (`CMD ["sh", "-c", "rm -f app.db && python site_1.py"]`). This means data will not persist across container restarts with the default configuration.

To create the database schema, you can use the `create_db.py` script. You might need to run this script *inside* the running container or modify the application/startup process to handle database creation and persistence.

**Option 1: Run `create_db.py` in a running container (after starting with `start.sh`):**
```bash
docker exec -it duckly-container python create_db.py
```

**Option 2: For a persistent database:**
*   Modify `site_1.py` to store `app.db` inside the `/app/instance` directory (e.g., `app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/app.db'`).
*   Ensure the `instance` directory exists locally before running `start.sh`.
*   Remove `rm -f app.db` from the `CMD` in the `Dockerfile` if the database is moved to the `instance` folder.

## Key Files

*   `site_1.py`: The core Flask application logic, including all routes, database models, and view functions.
*   `Dockerfile`: Instructions for building the Docker image.
*   `requirements.txt`: Lists all Python dependencies.
*   `start.sh`: Utility script to simplify building and running the Docker container.
*   `create_db.py`: Script to create the database tables based on the models defined in `site_1.py`.
*   `templates/`: Contains the HTML templates rendered by Flask.
*   `static/`: Contains static files like CSS and JavaScript.

## Potential Improvements / Areas to Note

*   **Database Persistence:** As mentioned, the current `Dockerfile` setup leads to an ephemeral database. This should be addressed for any practical use by ensuring the database file is stored in the mounted `instance` volume and not deleted on container start.
*   **Secret Key:** The `app.secret_key` in `site_1.py` is hardcoded. For production, this should be set via an environment variable or a configuration file.
*   **Volume Path in `start.sh`:** The `start.sh` script uses an absolute path (`/home/amir/Duckly/instance`) for the volume mount. This should be changed to a relative path (e.g., `-v $(pwd)/instance:/app/instance` for Linux/macOS or an equivalent for Windows) or parameterized to make the script more portable.
*   **Error Handling and Input Validation:** While some basic checks are present, robust error handling and comprehensive input validation would enhance the application's stability.
*   **Testing:** The presence of `test.py` suggests tests exist or are planned. Comprehensive test coverage is important.
*   **Security:** Review security aspects, especially around user authentication, authorization (teacher vs. student access), and protection against common web vulnerabilities (XSS, CSRF, SQL Injection - though SQLAlchemy helps mitigate the latter).

## Contributing

(Provide guidelines here if this is an open project, e.g., how to submit issues, feature requests, or pull requests.)

## License

(Specify the license for the project, e.g., MIT, GPL, etc.) 