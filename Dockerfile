# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Create the /app/data directory
RUN mkdir -p /app/data

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Run splatchain_discord.py when the container launches
CMD ["python", "splatchain_discord.py"]