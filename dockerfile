# Use Python 3 Alpine as the base image
FROM python:3.12-bookworm

# Set the timezone
ENV TZ="America/New_York"

# Set the working directory inside the container
WORKDIR /app

# Copy only necessary files
COPY main.py requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the bot
CMD ["python", "main.py"]