FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7

RUN mkdir -p /usr/src/app/webserver/logs
WORKDIR /usr/src/app/webserver


RUN mkdir -p /root/.pip

COPY requirements.txt ./
#RUN pip install --proxy=http://10.144.100.14:8080 --no-cache-dir -r requirements.txt
RUN pip install --proxy=http://10.144.100.14:8080 --no-cache-dir -r requirements.txt
#RUN pip install -r requirements.txt


COPY . .