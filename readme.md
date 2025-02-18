# Getting started
## Docker
### Pre-requisites
- Docker
- Docker-compose
### Steps
1. Clone the repository
2. Rename the file `compose.yml.example` to `compose.yml`
3. Change the variables in the file `compose.yml` under the `environment` key
4. Run the command `docker-compose build` to build the image
5. Run the command `docker-compose up` to start the container
## Local Python
### Pre-requisites
- Python 3.12
- Pip
### Steps
1. Clone the repository
2. Create a virtual environment using the command `python -m venv venv`
3. If on Windows, activate the virtual environment using the command `.\venv\Scripts\activate`
4. If on Linux, activate the virtual environment using the command `source venv/bin/activate`
5. Install the dependencies using the command `pip install -r requirements.txt`
6. Setup local environment variables
7. Run the command `python main.py`

# Recommendations
I'd recommend using Docker as it's easier to setup and run the application. If you're familiar with Python, you can use the local setup instead. This is a simple application and doesn't require much setup. It should really only be used on a single guild as it doesn't have any database support.