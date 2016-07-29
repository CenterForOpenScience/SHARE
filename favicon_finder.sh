#!/bin/bash

for f in $(find . -name 'apps.py' -type f);
do
    url_from=$(cat $f | grep 'home_page' | grep -o "'.*'" | sed "s/'//g";)
    if [ -n "$url_from" ]
    then
        var=`echo $f | sed -e 's/\/apps\.py//'`
        providerappname=`echo $f | sed -e 's/\/apps\.py//' | sed -e 's/\.\/providers\///' | sed -e 's/\//./g'`
        mkdir $var/static/; mkdir $var/static/$providerappname/; mkdir $var/static/$providerappname/img/; mkdir $var/static/$providerappname/img/favicon/
        cd $var/static/ && { curl -o $providerappname/img/favicon/favicon.ico http://www.google.com/s2/favicons?domain_url=$url_from ; cd -; }
    fi
done
