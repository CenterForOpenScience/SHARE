import behave
from django.conf import settings

from share import models
from share.disambiguation import GraphDisambiguator
from share.ingest.change_builder import ChangeBuilder
from share.regulate import Regulator
from share.util.graph import MutableGraph

from tests.factories import NormalizedDataFactory, ShareUserFactory


def accept_changes(context, nodes, username):
    user = models.ShareUser.objects.get(username=username)
    graph = MutableGraph.from_jsonld(nodes)
    Regulator().regulate(graph)
    instance_map = GraphDisambiguator(user.source).find_instances(graph)
    nd = NormalizedDataFactory(source=user)
    change_set = ChangeBuilder.build_change_set(graph, nd, instance_map)
    return change_set.accept() if change_set else None


def make_subjects(table, work_id=None):
    subjects = {}
    throughs = []

    def ref(node):
        if not node:
            return None
        return {'@id': node['@id'], '@type': node['@type']}

    for row in table:
        parent, synonym = None, None

        if row.get('PARENT'):
            parent = subjects.get(row['PARENT'])
            if not parent:
                parent = {'@id': '_:{}'.format(row['PARENT']), '@type': 'subject', 'name': row['PARENT']}
                subjects[row['PARENT']] = parent
        if row.get('SYNONYM'):
            synonym = subjects.get(row['SYNONYM'])
            if not synonym:
                synonym = {'@id': '_:{}'.format(row['SYNONYM']), '@type': 'subject', 'name': row['SYNONYM']}
                subjects[row['SYNONYM']] = synonym

        subject = {
            '@id': '_:{}'.format(row['NAME']),
            '@type': 'subject',
            'name': row['NAME'],
            'uri': row.get('URI'),
            'parent': ref(parent),
            'central_synonym': ref(synonym),
        }
        subjects[row['NAME']] = subject
        if work_id:
            throughs.append({
                '@id': '_:through_{}'.format(row['NAME']),
                '@type': 'throughsubjects',
                'creative_work': {'@id': work_id, '@type': 'creativework'},
                'subject': ref(subject),
            })
    return [*subjects.values(), *throughs]


@behave.given('a central taxonomy')
def add_central_taxonomy(context):
    accept_changes(context, make_subjects(context.table), settings.APPLICATION_USERNAME)


@behave.given('{username}\'s custom taxonomy')
def add_custom_taxonomy(context, username):
    accept_changes(context, make_subjects(context.table), username)


@behave.given('a user {username} with a source')
def add_user(context, username):
    ShareUserFactory(username=username)


@behave.when('{username} adds a work with subjects')
def add_work_with_subjects(context, username):
    work = {
        '@id': '_:worky',
        '@type': 'creativework',
        'title': 'title title',
    }
    nodes = accept_changes(context, [work, *make_subjects(context.table, work['@id'])], username)
    context.work = next(n for n in nodes if isinstance(n, models.AbstractCreativeWork))


@behave.then('central taxonomy exists')
@behave.then('{username}\'s custom taxonomy exists')
def taxonomy_exists(context, username=None):
    if not username:
        username = settings.APPLICATION_USERNAME
    assert models.SubjectTaxonomy.objects.filter(source__user__username=username).exists()


@behave.then('{count:d}{root}subjects exist in central taxonomy')
def count_central_subjects(context, count, root):
    count_subjects(context, count, root, settings.APPLICATION_USERNAME)


@behave.then('{count:d}{root}subjects exist')
@behave.then('{count:d}{root}subjects exist in {username}\'s custom taxonomy')
def count_subjects(context, count, root, username=None):
    qs = models.Subject.objects.all()
    if username is not None:
        qs = qs.filter(taxonomy__source__user__username=username)

    if root == ' root ':
        qs = qs.filter(parent__isnull=True)
    elif root != ' ':
        raise ValueError('Invalid root part: {}'.format(root))

    assert qs.count() == count


@behave.then('{custom_subject} is a synonym of {central_subject}')
def is_synonym(context, custom_subject, central_subject):
    custom = models.Subject.objects.get(name=custom_subject)
    assert custom.central_synonym.central_synonym_id is None
    assert custom.central_synonym.name == central_subject


@behave.then('{child_name} is a root')
@behave.then('{child_name} is a child of {parent_name}')
def is_child(context, child_name, parent_name=None):
    child = models.Subject.objects.get(name=child_name)
    if parent_name:
        assert child.taxonomy == child.parent.taxonomy
        assert child.parent.name == parent_name
    else:
        assert child.parent is None


@behave.then('{name} has depth {depth:d}')
def subject_depth(context, name, depth):
    lineage = models.Subject.objects.get(name=name).lineage()
    assert len(lineage) == depth
