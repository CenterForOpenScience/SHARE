# SHARE Quickstart or: How I Learned to Stop Worrying and Love the Dock

this guide sets up everything inside docker containers -- no dependencies
or python environments on your host machine.

## pre-requisites
- [git](https://git-scm.com/)
- [docker](https://www.docker.com/) (including `docker-compose`)

## getting a local SHARE running

### 0. git the code
```
git clone https://github.com/CenterForOpenScience/SHARE.git share
```
the rest of this guide assumes your working directory is the SHARE repository root
(where the `docker-compose.yml` is):
```
cd ./share
```

### 1. download several bits
download docker images (depending on your internet connection, this may take a beat):
```
docker-compose pull
```
install python dependencies (in a shared docker volume):
```
docker-compose up requirements
```

### 2. structured data
there are two services that store persistent data: `postgres` and `elasticsearch`

let's start them from the host machine:
```
docker-compose up -d postgres elasticsearch
```

since we're not installing anything more on the host machine, it'll be useful to open
a shell running within SHARE's environment in docker:
```
docker-compose run --rm --no-deps worker bash
```
this will open a bash prompt within a temporary `worker` container -- from here we can
use SHARE's python environment, including django's `manage.py` and SHARE's own `sharectl`
utility (defined in `share/bin/`)

from the worker shell, use django's `migrate` command to set up tables in postgres:
```
python manage.py migrate
```
and use `sharectl` to set up indexes in elasticsearch:
```
sharectl search setup --initial
```

### 3. start 'em up
all other services can now be started (from the host machine):
```
docker-compose up -d rabbitmq worker web indexer frontend
```

## handy commands

### start a docker shell

this is the same command you ran in step 2:

```
docker-compose run --rm --no-deps worker bash
```

### start a django shell

this should be run inside the docker shell (see previous):

```
python manage.py shell_plus
```

## admin interface
http://localhost:8003/admin -- (admin/password)

## harvesting data
TODO: once share.osf.io/oaipmh is reliable, make it easy to init a local deployment by harvesting data from there

also TODO: put some thought into unconvoluting the whole harvest-scheduling, ingest-disabling system

for now, maybe grab a day of data from arxiv.org? at the moment, the `Source` needs to be marked
`canonical` for the system to ingest its data -- either:
  - update it in the admin interface: http://localhost:8003/admin/share/source/
  - update it from the django shell:
    ```
    Source.objects.filter(name='org.arxiv').update(canonical=True)
    ```

you will also need to update the subject index from the docker shell:

```
python manage.py addsubjects
```

next choose a recent date, and start a harvest task for it from the docker shell:

```
sharectl schedule -t org.arxiv YYYY-MM-DD
```

you could watch its progress several different ways:
  - looking at task queues in the rabbitmq management interface at http://localhost:15673/ (guest/guest)
  - following the `worker` container's logs: `docker-compose logs -f worker`
  - watching the result count rise as you refresh the search interface at http://localhost:8003/share/discover

## troubleshooting
- does docker have enough memory? try giving it more
