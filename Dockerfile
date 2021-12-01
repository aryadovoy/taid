FROM python:3.10

RUN mkdir /usr/src/app

WORKDIR /usr/src/app

COPY * /usr/src/app/

RUN pip install -r requirements.txt

CMD [ "python", "taid.py" ]
