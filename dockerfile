# Use Python 3.12 as the base image
FROM python:3.12-bookworm
# RUN apt update && apt install git -y && git clone https://github.com/Pycord-Development/pycord && cd pycord && pip install .
# Set the timezone
ENV TZ="America/New_York"

# Set the working directory inside the container
WORKDIR /app

# Copy only necessary files
COPY main.py requirements.txt ./
COPY scryfall/ ./scryfall/
COPY not_scryfall/ ./not_scryfall/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the bot
CMD ["python", "main.py"]