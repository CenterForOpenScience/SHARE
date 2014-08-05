SHARE Notification Service Components at COS
=====

Core
-----

scrapi: http://www.github.com/fabianvf/scrapi

Prototype demo can be found at http://173.255.232.219/, and the current directory structure can be viewed at http://173.255.232.219/archive.

Data Consumption Projects
-----

ClinicalTrials.gov: https://github.com/erinspace/ClinicalTrials-consumer

PLOS: https://github.com/fabianvf/PLoS-API-consumer

SciTech: https://github.com/erinspace/pyscitech

Altmetric: https://github.com/CenterForOpenScience/PyAltmetric

ImpactStory: https://github.com/CenterForOpenScience/PyImpactStory

CrossRef: Evaluation of API and libraries by Xander.

eScholarship - University of California: https://github.com/erinspace/eScholarship/

DigitalCommons - Wayne State University: https://github.com/erinspace/DigitalCommonsWayneState

Virginia Tech VTechWorks - https://github.com/erinspace/VT-consumer -- Originally at https://github.com/webkunoichi/VT-consumer

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


Current Metadata Schema
-----

Here is the current state of our schema for resources consumed for SHARE - this schema
will be updated as the SHARE service matures. 

Here's the specification of we have so far: 

* **contributors** - a list of dictionaries containing email, full name, and ORCIDs of contributors.
* **id** - a dictionary of unique IDs given to the article based on the particular publication we’re accessing. Should include an entry for a URL that links right to the original resource, a DOI, and other entries as needed that include more unique IDs available in the original document. 
* **meta** -  metadata necessary for importing to the OSF (to be further clarified later...)
* **properties** - a dictionary containing elements of the article/study itself, sometimes within lists.  Can include figures, PDFs, or any other study data made readily available by the source API. Not all resources will have this information. 
* **description** - an abstract or general description of the resource
* **tags** - a list of tags or keywords identified in the resource itself
* **source** - a string identifying where the resource came from
* **timestamp** - string indicating when the article was accessed by scrAPI using the format YYYY-MM-DD h:m:s
* **date_created** - string indicating when the article was first created or published using the format YYYY-MM-DD
* **title**- string representing title of the article or study


Example from PLoS:

```json
{
    "contributors": [
        {
            "email": "loudonj@ecu.edu", 
            "full_name": "James E. Loudon",
            "ORCID": "add-orcid-here"
        }, 
    ], 
    "id": {
        "url": "http://www.plosone.org/article/info%3Adoi%2F10.1371%2Fjournal.pone.0100758", 
        "doi": "10.1371/journal.pone.0100758"
    },
    "meta": {"OSF specific metadata"}, 
    "properties": {
        "PDF": "http://dx.plos.org/10.1371/journal.pone.0100758.pdf", 
        "figures": ["http://www.plosone.org/article/fetchObject.action?uri=info:doi/10.1371/journal.pone.0100758.g001&representation=PNG_M"], 
        }, 
    "description": "This study seeks to understand how humans impact the dietary patterns of eight free-ranging vervet monkey (Chlorocebus pygerythrus) groups in South Africa using stable isotope analysis.", 
    "tags": [
        "Behavior"
    ]
    ,
    "source": "PLoS", 
    "timestamp": "2014-07-11 10:31:33.168456", 
    "date_created": "2014-07-10"
    "title": "PLOS ONE: Using Stable Carbon and Nitrogen Isotope Compositions"
}
```

