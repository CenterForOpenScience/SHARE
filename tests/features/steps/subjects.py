import behave
from django.conf import settings

from share import models
from share.change import ChangeGraph
from share.models import ChangeSet

from tests.factories import NormalizedDataFactory, ShareUserFactory


def accept_changes(context, nodes, user=None):
    user = (user or context.user)
    cg = ChangeGraph(nodes, namespace=user.username)
    cg.process()
    nd = NormalizedDataFactory(source=user)
    return ChangeSet.objects.from_graph(cg, nd.id).accept()


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


def taxonomy_name(context, taxonomy_type):
    if taxonomy_type == 'custom':
        return models.Source.objects.get(user=context.user).long_title
    if taxonomy_type == 'central':
        return settings.SUBJECTS_CENTRAL_TAXONOMY
    raise ValueError('Invalid taxonomy: {}'.format(taxonomy_type))


@behave.given('a central taxonomy')
def add_central_taxonomy(context):
    models.SubjectTaxonomy.objects.get_or_create(name=settings.SUBJECTS_CENTRAL_TAXONOMY)
    accept_changes(context, make_subjects(context.table), user=models.ShareUser.objects.get(username=settings.APPLICATION_USERNAME))


@behave.given('a custom taxonomy')
def add_custom_taxonomy(context):
    accept_changes(context, make_subjects(context.table))


@behave.given('a user with a source')
def add_user(context):
    context.user = ShareUserFactory()


@behave.when('a work is added with subjects')
def add_work_with_subjects(context):
    work = {
        '@id': '_:worky',
        '@type': 'creativework',
        'title': 'title title',
    }
    nodes = accept_changes(context, [work, *make_subjects(context.table, work['@id'])])
    context.work = next(n for n in nodes if isinstance(n, models.AbstractCreativeWork))


@behave.then('{taxonomy} taxonomy exists')
def taxonomy_exists(context, taxonomy):
    assert models.SubjectTaxonomy.objects.filter(name=taxonomy_name(context, taxonomy)).exists()


@behave.then('{count:d}{root}subjects exist')
@behave.then('{count:d}{root}subjects exist in {taxonomy} taxonomy')
def count_subjects(context, count, root, taxonomy=None):
    qs = models.Subject.objects.all()
    if taxonomy is not None:
        qs = qs.filter(taxonomy__name=taxonomy_name(context, taxonomy))

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
