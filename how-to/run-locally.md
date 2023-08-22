# SHARE Quickstart or: How I Learned to Stop Worrying and Love the Dock

this guide guides you through setting up SHARE locally using Docker
for development and manual testing.

this guide does NOT guide you to anything appropriate for the open Internet.


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
there are two services that store more-or-less persistent data: `postgres` and `elastic8`

let's start them from the host machine:
```
docker-compose up -d postgres elastic8
```

since we're not installing anything more on the host machine, it'll be useful to open
a shell running within SHARE's environment in docker:
```
docker-compose run --rm --no-deps worker bash
```
this will open a bash prompt within a temporary `worker` container -- from here we can
run commands within SHARE's environment, including django's `manage.py` and SHARE's own
`sharectl` utility (defined in `share/bin/`)

from within that worker shell, use django's `migrate` command to set up tables in postgres:
```
python manage.py migrate
```
...and use `sharectl` to set up indexes in elasticsearch:
```
sharectl search setup --initial
```

### 3. start 'em up
all other services can now be started from the host machine (upping `worker` ups all)
```
docker-compose up -d worker
```

## using with local [osf.io](https://github.com/CenterForOpenScience/osf.io)
0. [set up your local osf with docker](https://github.com/CenterForOpenScience/osf.io/blob/HEAD/README-docker-compose.md), if you haven't already
1. in a SHARE container, run `python manage.py add_local_osf_user` and copy the access token from the output.
    ```
    # python manage.py add_local_osf_user
    added user "my-local-osf" for local osf
    access-token: THISISMYACCESSTOKENITISLONGANDINSCRUTABLEANDSECRET
    ```
2. add settings to your local osf's `website/settings/local.py`, including the access token from step 1:
    ```
    SHARE_ENABLED = True
    SHARE_PROVIDER_PREPEND = 'local'
    SHARE_URL = 'http://192.168.168.167:8003/'
    SHARE_API_TOKEN = 'THISISMYACCESSTOKENITISLONGANDINSCRUTABLEANDSECRET'
    ```
    (you may need to restart osf services that use these settings)
3. use the osf admin interface at `http://localhost:8001` to connect osf providers (can skip this step if you're only interested in osf:Project records)
    1. at `/provider_asset_files/create`, add a small icon (PNG or JPEG) with name `square_color_no_transparent` for the provider(s) you want
    2. on each provider detail page (e.g. `/preprint_provider/<id>/`), click the "Setup Share Source" button
    > TODO: streamline this process -- is the icon really necessary?
4. make things "public" on your local osf to start populating indexes


> TODO: make it easy to init a local deployment by harvesting data from share.osf.io

## handy commands

### start a shell in a container
there are several ways to open a shell with SHARE's environment (which has
django's `manage.py` and SHARE's own `sharectl` utility, defined in `share/bin/`)

if `worker` is already up, can open a shell within that container:
```
docker-compose exec worker bash
```

if no services are up, can open a shell within a new, temporary `worker` container:
```
docker-compose run --rm --no-deps worker bash
```
(remove `--no-deps` if you'd like the other services started automatically)

### start a django shell
this should be run inside a container (see previous):

```
python manage.py shell_plus
```

## admin interface
http://localhost:8003/admin (username: "admin", password: "password")

## troubleshooting
- my containers keep mysteriously dying!
  - does docker have enough memory? try giving it more
