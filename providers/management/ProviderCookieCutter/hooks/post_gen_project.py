

import requests

url = 'static/{}.{}/img/favicon.ico'.format('{{cookiecutter.domain}}', '{{cookiecutter.title}}')

with open(url, 'wb') as favicon:
    print('Trying to get favicon...')
    r = requests.get('{{cookiecutter.home_page}}' + '/favicon.ico')
    if r.status_code == 200:
        favicon.write(r.content)
    else:
        print('Favicon pull unsuccessful from ' + url)
