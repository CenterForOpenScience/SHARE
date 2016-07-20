#!/bin/bash

for f in $(find . -name 'apps.py' -type f);
do
    url_from=$(cat $f | grep 'home_page' | grep -o "'.*'" | sed "s/'//g";)
    if [ -n "$url_from" ]
    then
        var=`echo $f | sed -e 's/\/apps\.py//'`
        mkdir $var/static
        cd $var/static && { curl -o favicon.ico http://www.google.com/s2/favicons?domain_url=$url_from ; cd -; }
    fi
done
