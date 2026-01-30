#FROM python:3.12.3
FROM python:3.12-slim-bullseye

# Install Java (OpenJDK)
RUN apt-get update && apt-get install -y \
    openjdk-11-jdk \
    && apt-get clean

# Set the JAVA_HOME environment variable
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV PATH="$JAVA_HOME/bin:$PATH"

# Set up the python environment 
COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY . /app/

WORKDIR /app

CMD [ "python", "main.py" ]