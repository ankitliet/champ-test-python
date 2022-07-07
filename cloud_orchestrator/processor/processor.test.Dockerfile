FROM python:3.9-slim-buster

RUN mkdir -p /usr/src/app/terrafiles
RUN chmod 777 /usr/src/app/terrafiles

RUN mkdir -p /usr/src/app/armtemplates
RUN chmod 777 /usr/src/app/armtemplates

RUN mkdir -p /usr/src/app/hcmp_orchestrator_processor/logs
WORKDIR /usr/src/app/hcmp_orchestrator_processor

#RUN export http_proxy=10.144.100.14:8080 && export https_proxy=10.144.100.14:8080
#ENV http_proxy 'http://10.144.100.14:8080'
#ENV https_proxy 'http://10.144.100.14:8080'
#ENV no_proxy '10.166.168.80,10.144.99.230,10.157.253.253'
#RUN export no_proxy=10.166.168.80,10.144.99.230,10.157.253.253

RUN export ARM_SKIP_PROVIDER_REGISTRATION=true

RUN mkdir -p /root/.pip

RUN apt-get update -y
RUN apt-get install git -y
RUN apt-get install ansible -y
RUN git config --global http.sslVerify false
RUN apt-get install wget unzip curl -y
RUN wget https://releases.hashicorp.com/terraform/1.0.5/terraform_1.0.5_linux_amd64.zip
RUN unzip terraform_1.0.5_linux_amd64.zip
RUN mv terraform /usr/local/bin/


COPY processor/requirements.txt ./
#RUN pip install --proxy=http://10.144.100.14:8080 --no-cache-dir -r requirements.txt
RUN pip install -r requirements.txt
RUN ansible-galaxy collection install community.general
RUN ansible-galaxy collection install ansible.posix
RUN ansible-galaxy collection install ansible.windows
RUN ansible-galaxy collection install community.windows
RUN ansible-galaxy install geerlingguy.mysql
RUN ansible-galaxy collection install community.mysql
RUN mkdir -p /usr/share/ansible
RUN mkdir -p /usr/share/ansible/collections


COPY processor ./processor/
COPY consumer ./consumer/
COPY util ./util/
COPY resource_adapters ./resource_adapters/
COPY ./processor/start-local.sh ./
COPY ./processor/update_openstack_lib.py ./

RUN curl -fsSL https://raw.githubusercontent.com/infracost/infracost/master/scripts/install.sh | sh
ENV INFRACOST_PRICING_API_ENDPOINT='http://13.126.60.149:4000'
ENV INFRACOST_API_KEY='0gcq6E8A6QRTbP3em9Rof6k4ahuMHr4W'

COPY processor/askpass.py /usr/src/app/terrafiles/
RUN chmod 777 /usr/src/app/terrafiles/
RUN chmod 777 /usr/src/app/terrafiles/askpass.py
#RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash

RUN chmod +x /usr/src/app/hcmp_orchestrator_processor/update_openstack_lib.py
RUN /usr/local/bin/python /usr/src/app/hcmp_orchestrator_processor/update_openstack_lib.py


RUN chmod +x /usr/src/app/hcmp_orchestrator_processor/start-local.sh
CMD ["/usr/src/app/hcmp_orchestrator_processor/start-local.sh"]
