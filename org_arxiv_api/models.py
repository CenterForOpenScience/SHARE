from django.db import models

# Create your models here.
class HarvesterOrgArxivApi(shareharvestermodell):
    SCHEMA =
    id = models.CharField(max_length=200)
    title = models.CharField(max_length=500)
    date_published = models.DateTimeField('date published')

Migrate(Manuscripts, new="arxiv_cat:charfield")

class ArxivManuscripts(Manuscripts):
    arxiv_cat = models.CharField()

class DataCite(Data):


