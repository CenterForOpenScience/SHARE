FROM python:3.5-slim

RUN apt-get update \
    && apt-get install -y \
        ca-certificates \
        gcc \
        git \
        libxml2-dev \
        libxslt1-dev \
        libffi-dev \
        # psycopg2
        python-dev \
        libpq-dev \
    && apt-get clean \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

RUN update-ca-certificates

RUN mkdir -p /code
WORKDIR /code

RUN pip install -U pip

COPY ./requirements.txt /code/requirements.txt
COPY ./constraints.txt /code/constraints.txt

RUN pip install --no-cache-dir -c /code/constraints.txt -r /code/requirements.txt

RUN apt-get remove -y gcc

COPY ./ /code/

CMD ["python", "manage.py", "--help"]
