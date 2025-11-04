# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the requirements file into the container at /usr/src/app
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY . .

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Run the command to initialize the database and create the admin user
RUN flask db init || true && \
    flask db migrate -m "Initial migration." || true && \
    flask db upgrade || true && \
    flask create_apikey admin || true

# Define environment variable
ENV FLASK_APP run.py

# Run the app.py file when the container launches
CMD ["flask", "run", "--host=0.0.0.0"]
