FROM apache/airflow:2.9.0-python3.9

COPY requirements.txt .

USER root

# Install dependencies
RUN apt-get update && apt-get install -y \
    wget \
    firefox-esr \
    libgtk-3-0 \
    libdbus-glib-1-2 \
    libx11-xcb1 \
    libxtst6 \
    libxrender1 \
    libxrandr2 \
    libxcb-shm0 \
    libasound2 \
    libnss3 \
    libegl1-mesa \
    libfontconfig1 \
    libglib2.0-0 \
    xvfb

# Download and install geckodriver
RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.34.0/geckodriver-v0.34.0-linux64.tar.gz \
    && tar -xzf geckodriver-v0.34.0-linux64.tar.gz \
    && mv geckodriver /usr/local/bin/ \
    && chmod +x /usr/local/bin/geckodriver \
    && rm geckodriver-v0.34.0-linux64.tar.gz

COPY init_airflow.sh /usr/local/bin/init_airflow.sh
RUN chmod +x /usr/local/bin/init_airflow.sh

USER airflow
RUN pip install -r requirements.txt

ENTRYPOINT ["/usr/local/bin/init_airflow.sh"]
CMD ["webserver"]
