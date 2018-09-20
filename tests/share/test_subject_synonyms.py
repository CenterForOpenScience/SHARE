import json
import yaml

from django.conf import settings


def test_synonyms_valid():
    with open(settings.SUBJECTS_YAML) as f:
        subjects = yaml.load(f)
    subject_names = set(s['name'] for s in subjects)

    with open(settings.SUBJECT_SYNONYMS_JSON) as f:
        synonyms = json.load(f)
    mapped_subjects = set(s for syns in synonyms.values() for s in syns)

    diff = mapped_subjects - subject_names
    assert not diff
