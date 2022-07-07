#FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7
FROM nexuscoe.xxx.com:5115/ngo/cloudorch-api-image:latest

RUN mkdir -p /usr/src/app/webserver/logs
WORKDIR /usr/src/app/webserver

RUN mkdir -p /root/.pip

COPY . .

RUN mkdir -p /mnt/logs
RUN chmod 777 /mnt/logs

RUN chmod +x /usr/src/app/webserver/fastapi_webserver/start.sh

CMD ["/usr/src/app/webserver/fastapi_webserver/start.sh"]