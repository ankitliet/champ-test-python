#FROM python:3.9-slim-buster
#FROM nexuscoe.xxx.com:5115/ngo/python-3
FROM nexuscoe.xxx.com:5115/ngo/cloudorch-processor-image:latest

RUN mkdir -p /usr/src/app/terrafiles
RUN chmod 777 /usr/src/app/terrafiles

RUN mkdir -p /usr/src/app/armtemplates
RUN chmod 777 /usr/src/app/armtemplates

RUN mkdir -p /usr/src/app/hcmp_orchestrator_processor/logs
WORKDIR /usr/src/app/hcmp_orchestrator_processor

RUN ansible-galaxy collection install community.general
RUN ansible-galaxy collection install ansible.posix
RUN ansible-galaxy collection install ansible.windows
RUN ansible-galaxy collection install community.windows
RUN ansible-galaxy install geerlingguy.mysql
RUN ansible-galaxy collection install community.mysql
RUN mkdir -p /usr/share/ansible
RUN mkdir -p /usr/share/ansible/collections

#RUN export http_proxy=10.144.100.14:8080 && export https_proxy=10.144.100.14:8080
ENV http_proxy "http://10.144.100.14:8080"
ENV https_proxy "http://10.144.100.14:8080"
ENV no_proxy '10.166.168.80,10.144.99.230,10.157.253.253'
RUN export no_proxy=10.166.168.80,10.144.99.230,10.157.253.253

RUN mkdir -p /root/.pip

RUN mkdir -p /mnt/logs
RUN chmod +x /mnt/logs

COPY processor ./processor/
COPY consumer ./consumer/
COPY util ./util/
COPY resource_adapters ./resource_adapters/
COPY ./processor/start.sh ./

COPY processor/askpass.py /usr/src/app/terrafiles/
RUN chmod 777 /usr/src/app/terrafiles/askpass.py

RUN mkdir -p /usr/src/app/terrafiles
RUN chmod 777 /usr/src/app/terrafiles

RUN chmod +x /usr/src/app/hcmp_orchestrator_processor/start.sh

CMD ["/usr/src/app/hcmp_orchestrator_processor/start.sh"]