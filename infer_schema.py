from util import infer_jsonschema
import feedparser
import jsonschema
# import vcr
import arrow
import json
import os

import django
from django.utils import timezone

# # with vcr.use_cassette('org.arxiv.api.201604248.3.yaml'):

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'share.settings')

django.setup()
from raw.models import Raw

js = infer_jsonschema(Raw.objects.all()[0].data[0], hints={
    "published": "date-time",
    "updated": "date-time"
})
print(js)

with open('org.arxiv.api.example.json', 'w') as f:
    json.dump(Raw.objects.all()[0].data[0], f, indent=True)

with open('org.arxiv.api.schema.json', 'w') as f:
    json.dump(js, f, indent=True)

# with open('org.arxiv.api.schema.json', 'w') as f:
#     json.dump(js, f, indent=True)
#
# class Format(dict):
#     def __init__(self, d, mapping):
#         for key, value in mapping.items():
#             d[key] = value(d[key])
#         self.update(d)
#
# for entry in feed.entries:
#     jsonschema.validate(Format(entry, {
#         'published': lambda x: arrow.get(x).format('YYYY-MM-DDTHH:mm:ssZZ'),
#         'published_parsed': lambda x: arrow.get(x).format('YYYY-MM-DDTHH:mm:ssZZ'),
#         'updated': lambda x: arrow.get(x).format('YYYY-MM-DDTHH:mm:ssZZ'),
#         'updated_parsed': lambda x: arrow.get(x).format('YYYY-MM-DDTHH:mm:ssZZ')
#     }), js)
