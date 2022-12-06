FROM python:3.11-slim as app

RUN apt-get update \
    && apt-get install -y \
        ca-certificates \
        gcc \
        git \
        gosu \
        libev4 \
        libev-dev \
        libevent-dev \
        libxml2-dev \
        libxslt1-dev \
        libffi-dev \
        # psycopg2
        python-dev \
        libpq-dev \
        zlib1g-dev \
    && apt-get clean \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

RUN update-ca-certificates

RUN mkdir -p /code
WORKDIR /code

RUN pip install -U pip
RUN pip install uwsgi==2.0.16

COPY ./requirements.txt /code/requirements.txt
COPY ./constraints.txt /code/constraints.txt

RUN pip install --no-cache-dir -c /code/constraints.txt -r /code/requirements.txt

RUN apt-get remove -y \
    gcc \
    zlib1g-dev

COPY ./ /code/

RUN python manage.py collectstatic --noinput

ARG GIT_TAG=
ARG GIT_COMMIT=
ENV VERSION ${GIT_TAG}
ENV GIT_COMMIT ${GIT_COMMIT}

RUN python setup.py develop

CMD ["python", "manage.py", "--help"]

### Dist
FROM app AS dist

### Dev
FROM app AS dev

RUN pip install --no-cache-dir -c /code/constraints.txt -r /code/dev-requirements.txt
