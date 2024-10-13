#!/bin/bash

# Step 0: Stop any running PostgreSQL containers
echo "Stopping any running PostgreSQL Docker containers..."
docker-compose down

# Step 1: Run docker-compose to set up PostgreSQL
echo "Starting PostgreSQL with Docker..."
docker-compose up -d

# Step 2: Update requirements.txt from requirements.in (using pip-tools)
# Make sure pip-tools is installed
if ! command -v pip-compile &> /dev/null
then
    echo "pip-compile not found, installing pip-tools..."
    pip install pip-tools
fi

echo "Updating requirements.txt from requirements.in..."
pip-compile requirements.in

# Step 3: Install dependencies from requirements.txt
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# Step 4: Run the main.py file
echo "Running main.py..."
python src/main.py

# Step 5: Run unit tests with coverage
echo "Running unit tests with coverage..."
coverage run -m unittest discover -s tests

# Step 6: Generate unit test coverage report
echo "Generating coverage report..."
coverage report
coverage html

# Step 7: Show completion message
echo "PostgreSQL is up and running, data ingested and loaded into db, and coverage report created."

# Step 8: Generate streamlit report
echo "Generating streamlit report..."
streamlit run streamlit/app.py

# Step 9: Stop any running PostgreSQL containers once streamlit app stopped
echo "Stopping any running PostgreSQL Docker containers..."
docker-compose down
