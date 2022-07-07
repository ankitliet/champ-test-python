FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7

RUN mkdir -p /usr/src/app/webserver/logs
WORKDIR /usr/src/app/webserver

RUN mkdir -p /root/.pip

RUN ls -la

#COPY . .

RUN ls -la
COPY fastapi_webserver/requirements.txt ./
#RUN pip install --proxy=http://10.144.100.14:8080 --no-cache-dir -r requirements.txt
#RUN pip install --proxy=http://10.144.100.14:8080 --no-cache-dir -r requirements.txt
RUN pip install -r requirements.txt

COPY fastapi_webserver/localhost.crt fastapi_webserver/
COPY fastapi_webserver/localhost.key fastapi_webserver/

COPY . .

RUN ls -la

#COPY /opt/htcinx/cloudAutomation/micro-services/util /usr/src/app

#RUN ls -la /usr/src/app/
RUN ls -la /usr/src/app/webserver

RUN mkdir -p /mnt/logs
RUN chmod 777 /mnt/logs

RUN chmod +x /usr/src/app/webserver/fastapi_webserver/start.sh

CMD ["/usr/src/app/webserver/fastapi_webserver/start.sh"]
