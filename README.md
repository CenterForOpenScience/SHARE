SHARE Notification Service Components at COS
=====

Core
-----

scrapi: http://www.github.com/fabianvf/scrapi

Prototype demo can be found at http://173.255.232.219/

Data Consumption Projects
-----

ClinicalTrials.gov: https://github.com/pjfan/ClinicalTrialsParser

PLOS: https://github.com/fabianvf/PLoS-API-consumer

SciTech: https://github.com/erinspace/pyscitech

Altmetric: https://github.com/CenterForOpenScience/PyAltmetric

ImpactStory: https://github.com/CenterForOpenScience/PyImpactStory

CrossRef: Evaluation of API and libraries by Xander.

arXiv: Evaluation started by Peter.

OAI-PMH: Evaluation being conducted by Casey.

Conflict Management
-----

Casey and Faye evaluated and prototyped conflict management with [FuzzyWuzzy](https://github.com/seatgeek/fuzzywuzzy). On hold until Core is further developed.


Using the issue tracker
-----

Please include one of these tags at the beginning of your issue title.

[core]:  An issue regarding SHARE core, also known as scrAPI.

[schema]: An issue regarding the defined representations of document types, such as what information might be required for a submission to be considered an article, citation, or dataset, or what types of information should be searchable.

[content provider]: Information about a new service to be added to scrAPI that (1) is on the SHARE priority list and has been vetted and met required SHARE criteria or (2) may be a priority for other reasons and has an API. Once technical evaluation is completed, a new issue with the tag [consumer] should be created, and the [content provider] issue should be closed with a link to the new issue.  

[consumer]: An issue regarding a consumer that is currently being developed. These issues should include a link to the primary github repo for the consumer. Consumer in this context means an application which accesses a service via API, consumes the content, and normalizes it for inclusion in the search engine in scrAPI. Note that this is distinct from "consumer" in the context of the [SHARE Notification Service Architectural Overview](http://www.arl.org/storage/documents/publications/SHARE-notification-service-architectural-overview-14apr2014.pdf) where "consumer" refers to the subscriber to notifications.

About SHARE
-----

SHARE (SHared Access Research Ecosystem) and the Center for Open Science (COS), a Charlottesville, Virginia–based nonprofit technology start-up, have agreed to form a partnership to build the SHARE Notification Service, which will provide notice that research is available to the public.

SHARE is a collaborative initiative of the Association of Research Libraries (ARL), the Association of American Universities (AAU), and the Association of Public and Land-grant Universities (APLU), created to ensure the preservation of, access to, and reuse of research results. The Notification Service, to be built over the next 18 months, is SHARE’s first project.

The Institute of Museum and Library Services (IMLS) and the Alfred P. Sloan Foundation have generously provided grant funding to develop the open source Notification Service, which will enable scholars, funders, university research offices, institutional and disciplinary repositories, and the public to identify when a publication, data set, or other research output is available.

Interested parties have found it difficult to keep abreast of the release of publications, data sets, and other results of scholarly research. Across the disciplines, principal investigators and other scholars do not have any single, structured way to report these releases in a timely and comprehensive manner. The SHARE Notification Service is a higher education-based initiative to strengthen efforts to identify, discover, and track research outputs.

The COS’s mission to foster openness, integrity, and reproducibility of research is well aligned with SHARE’s objectives. Andrew Sallans, COS partnerships manager, has participated in SHARE’s Technical Working Group since November 2013.

“We are excited to partner with ARL, AAU, and APLU on this important community effort,” Sallans said. “This is a great opportunity to collectively build a solution that will serve many stakeholders across the entire research process.”

The Notification Service will make use of the Open Science Framework (OSF), COS’s existing, free, open-source platform designed to connect the scholarly workflow.

“We strongly believe that ensuring broad and continuing access to research is central to the mission of higher education,” ARL executive director Elliott Shore said. “We are thrilled to partner with the Center for Open Science in this endeavor. Their mission is in sync with ours and their talents are exactly what we need to make the SHARE Notification Service a success.”

AAU executive vice president John Vaughn said, “We are delighted that SHARE has reached this important milestone in its plan to provide timely public access to the results of research. COS is well suited to help SHARE carry out this project.”

“We are very pleased that the SHARE Notification Service is moving forward and are excited to have the Center for Open Science as a partner,” APLU vice president and chief academic officer Michael Tanner said. “Working with COS will help us ensure that university research findings are easily accessible to the public and can be used to advance society and develop new breakthroughs.”

SHARE (SHared Access Research Ecosystem) is a higher education and research community initiative to ensure the preservation of, access to, and reuse of research outputs. SHARE will develop solutions that capitalize on the compelling interest shared by researchers, libraries, universities, funding agencies, and other key stakeholders to maximize research impact, today and in the future. SHARE aims to make the inventory of research assets more discoverable and more accessible, and to enable the research community to build upon these assets in creative and productive ways. The Association of Research Libraries (ARL), the Association of American Universities (AAU), and the Association of Public and Land-grant Universities (APLU) have partnered to develop SHARE with significant input from the three associations’ member institutions and their broader communities.
