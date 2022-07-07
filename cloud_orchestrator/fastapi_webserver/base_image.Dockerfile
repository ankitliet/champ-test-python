FROM nexuscoe.xxxx.com:5115/ngo/python-3

RUN mkdir -p /root/.pip

COPY requirements.txt ./

RUN pip install --proxy=http://10.144.100.14:8080 --no-cache-dir -r requirements.txt