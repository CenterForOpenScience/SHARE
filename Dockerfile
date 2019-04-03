FROM python:3.6-slim-stretch as app

RUN apt-get update \
    && apt-get install -y \
        ca-certificates \
        gcc \
        git \
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

# gosu
ENV GOSU_VERSION 1.10
RUN apt-get update \
    && apt-get install -y \
        curl \
        gnupg2 \
    && mkdir ~/.gnupg && chmod 600 ~/.gnupg && echo "disable-ipv6" >> ~/.gnupg/dirmngr.conf \
    && for server in hkp://ipv4.pool.sks-keyservers.net:80 \
                     kp://ha.pool.sks-keyservers.net:80 \
                     hkp://pgp.mit.edu:80 \
                     hkp://keyserver.pgp.com:80 \
    ; do \
        gpg --keyserver "$server" --recv-keys B42F6819007F00F88E364FD4036A9C25BF357DD4 && break || echo "Trying new server..." \
    ; done \
    && curl -o /usr/local/bin/gosu -SL "https://github.com/tianon/gosu/releases/download/$GOSU_VERSION/gosu-$(dpkg --print-architecture)" \
    && curl -o /usr/local/bin/gosu.asc -SL "https://github.com/tianon/gosu/releases/download/$GOSU_VERSION/gosu-$(dpkg --print-architecture).asc" \
    && gpg --verify /usr/local/bin/gosu.asc \
    && rm /usr/local/bin/gosu.asc \
    && chmod +x /usr/local/bin/gosu \
    # /gosu
    && apt-get clean \
    && apt-get autoremove -y \
        curl \
        gnupg2 \
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
