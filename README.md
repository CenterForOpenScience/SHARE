SHARE Notification Service Components at COS
=====

More information available in the [SHARE Development Wiki](https://osf.io/wur56/wiki/home/)
-----

On the github wiki page you'll find detailed information about...
* [the SHARE project](https://osf.io/t3j94)
* [the current SHARE schema for the consumers](https://osf.io/t3j94/)
* [how to use the issue tracker](https://github.com/CenterForOpenScience/SHARE/wiki/Using-the-Issue-Tracker)
* [project and harvester architecture](https://osf.io/wur56/wiki/scrAPI/)

Core
-----

scrapi: http://www.github.com/fabianvf/scrapi

 A pre-beta application can be found at https://osf.io/share. There are a variety of output formats provided by the API, the links are listed below:

JSON: https://osf.io/api/v1/share/search

Atom: https://osf.io/share/atom


Harvester Projects
-----
Harvesters are included within scrapi.

You can see the code for each harvester at https://github.com/fabianvf/scrapi/tree/master/scrapi/harvesters


Conflict Management
-----

Casey and Faye evaluated and prototyped conflict management with [FuzzyWuzzy](https://github.com/seatgeek/fuzzywuzzy). On hold until Core is further developed.

