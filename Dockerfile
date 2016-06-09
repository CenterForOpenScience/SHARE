FROM alpine:3.4

RUN apk add --no-cache \
      ca-certificates \
      postgresql-dev \
      python3-dev \
      libffi-dev \
      musl-dev \
      python3 \
      gcc \
    && update-ca-certificates

RUN mkdir -p /code
WORKDIR /code

RUN pip3 install -U pip

COPY ./requirements.txt /code/requirements.txt
COPY ./constraints.txt /code/constraints.txt

RUN pip3 install --no-cache-dir -c /code/constraints.txt -r /code/requirements.txt

RUN apk del gcc

COPY ./ /code/

CMD ["python3", "manage.py"]
