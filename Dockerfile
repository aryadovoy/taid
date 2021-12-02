FROM python:3.10-slim

RUN mkdir /home/app

WORKDIR /home/app

COPY requirements.txt /home/app/

RUN pip install -r requirements.txt

COPY proxy.py secret.py taid* /home/app/

ENTRYPOINT [ "python", "taid.py" ]
