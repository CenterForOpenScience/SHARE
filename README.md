SHARE Notification Service Components at COS
=====

Here, you can post issues related to SHARE, SHARE Notify, or the [beta application built on the Open Science Framework (OSF) using SHARE Data](http://osf.io/share)
* [how to use the issue tracker](https://github.com/CenterForOpenScience/SHARE/wiki/Using-the-Issue-Tracker)

More information available in the [SHARE Development Documentation](https://osf.io/wur56/wiki/home/)

More information about SHARE available on the [SHARE Homepage]() or the [main SHARE Documentation on the OSF]()


Core
-----
ScrAPI is a data processing pipeline that harvests information from many external providers and normalizes them for consumption into SHARE Notify. 

You can find the scraAPI code on github at http://www.github.com/fabianvf/scrapi
Issues specific to scrAPI internals are filed and tracked under [scrAPI's issue tracker on github](https://github.com/fabianvf/scrapi/issues).

Documentation on scrAPI can be found in [the SHARE Documentation on scrAPI](https://osf.io/wur56/wiki/scrAPI/) hosted on the Open Science Framework.

Using SHARE
-----------
For more documentation on using the various output options for SHARE content, see the [SHARE documentation on Feed Options](https://osf.io/wur56/wiki/Feed%20Options/) hosted on the OSF.

There are a variety of output formats provided by the API, the links are listed below:

JSON: https://osf.io/api/v1/share/search
Atom: https://osf.io/share/atom

A beta application built using the SHARE JSON API can be found at https://osf.io/share. 


Harvesters
-----
Harvesters are included within scrAPI, the data processing pipeline making up SHARE core.

You can see the code for each harvester at https://github.com/fabianvf/scrapi/tree/master/scrapi/harvesters


Conflict Management
-----

Casey and Faye evaluated and prototyped conflict management with [FuzzyWuzzy](https://github.com/seatgeek/fuzzywuzzy). On hold until Core is further developed.

