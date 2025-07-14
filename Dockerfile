FROM python:3.13-slim-bullseye AS app

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

# set working directory once, use relative paths from "./"
RUN mkdir -p /code
WORKDIR /code

###
# python dependencies

# note: installs dependencies on the system, roundabouts `/usr/local/lib/python3.13/site-packages/`

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_OPTIONS_ALWAYS_COPY=1 \
    POETRY_VIRTUALENVS_CREATE=0 \
    POETRY_VIRTUALENVS_IN_PROJECT=0 \
    POETRY_CACHE_DIR=/tmp/poetry-cache \
    POETRY_HOME=/tmp/poetry-venv

RUN python -m venv $POETRY_HOME

RUN $POETRY_HOME/bin/pip install poetry==2.1.3

COPY pyproject.toml poetry.lock ./

RUN $POETRY_HOME/bin/poetry install --compile --no-root

COPY ./ ./

RUN $POETRY_HOME/bin/poetry install --compile --only-root

RUN python manage.py collectstatic --noinput

ARG GIT_TAG=
ARG GIT_COMMIT=
ENV VERSION=${GIT_TAG}
ENV GIT_COMMIT=${GIT_COMMIT}

CMD ["python", "manage.py", "--help"]

### Dev
FROM app AS dev

RUN $POETRY_HOME/bin/poetry install --compile --only dev

### Dist
FROM app AS dist

RUN $POETRY_HOME/bin/poetry install --compile --only deploy

# remove packages needed only for install
RUN apt-get remove -y \
        gcc \
        zlib1g-dev \
    && apt-get clean \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/poetry-*
