FROM python:3.12-slim

RUN mkdir /srv/app

WORKDIR /srv/app

COPY requirements.txt /srv/app/

RUN pip install -r requirements.txt

COPY proxy.py secret.py taid* /srv/app/

ENTRYPOINT [ "python", "taid.py" ]
