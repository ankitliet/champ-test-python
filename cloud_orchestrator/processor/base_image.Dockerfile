FROM python:3.9-slim-buster

#RUN export http_proxy=10.144.100.14:8080 && export https_proxy=10.144.100.14:8080
ENV http_proxy 'http://10.144.100.14:8080'
ENV https_proxy 'http://10.144.100.14:8080'
ENV no_proxy '10.144.99.230,10.157.253.253'
RUN export no_proxy=10.144.99.230,10.157.253.253

RUN export ARM_SKIP_PROVIDER_REGISTRATION=true

RUN mkdir -p /root/.pip

RUN apt-get update -y
RUN apt-get install git -y
#RUN apt-get install ansible -y
RUN git config --global http.sslVerify false
RUN apt-get install wget unzip curl -y
RUN wget https://releases.hashicorp.com/terraform/1.0.5/terraform_1.0.5_linux_amd64.zip
RUN unzip terraform_1.0.5_linux_amd64.zip
RUN mv terraform /usr/local/bin/

COPY requirements.txt ./
RUN pip install --proxy=http://10.144.100.14:8080 --no-cache-dir -r requirements.txt
#RUN pip install -r requirements.txt

RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash
COPY ./update_openstack_lib.py ./
RUN chmod +x ./update_openstack_lib.py
RUN /usr/local/bin/python ./update_openstack_lib.py