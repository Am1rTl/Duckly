# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
# (Create this file if you have more dependencies)
RUN pip install --no-cache-dir Flask Flask-SQLAlchemy markupsafe PyMySQL psycopg2-binary # Added PyMySQL and psycopg2-binary as common DB drivers, adjust if needed
RUN pip install --no-cache-dir gunicorn # Gunicorn is a good WSGI server for production

# Make port 5000 available to the world outside this container
# This is the port your Flask app runs on internally in the container
EXPOSE 5000

# Define environment variables (if any, e.g., for database connections)
# ENV FLASK_APP site_1.py # Your main app file
# ENV FLASK_RUN_HOST 0.0.0.0

# Command to run the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "site_1:app"]