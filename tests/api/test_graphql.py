import pytest
from collections import OrderedDict

from share.graphql import schema
from share.util import IDObfuscator

from tests import factories


@pytest.mark.django_db
class TestCreativeWorks:

    query = '''
        query {
        }
    '''

    def test_basic_case(self):
        x = factories.AbstractCreativeWorkFactory()
        source = factories.SourceFactory()
        x.sources.add(source.user)

        # Have to use % formats because of {}s everywhere
        result = schema.execute('''
            query {
                creativeWork(id: "%s") {
                    id,
                    title,
                    description,
                    sources {
                        title
                    }
                }
            }
        ''' % (IDObfuscator.encode(x), ))

        assert not result.errors

        assert result.data == OrderedDict([
            ('creativeWork', OrderedDict([
                ('id', IDObfuscator.encode(x)),
                ('title', x.title),
                ('description', x.description),
                ('sources', [
                    OrderedDict([('title', source.long_title)])
                ])
            ]))
        ])

    def test_deleted_sources(self):
        x = factories.AbstractCreativeWorkFactory()
        source = factories.SourceFactory(is_deleted=True)
        x.sources.add(source.user)

        # Have to use % formats because of {}s everywhere
        result = schema.execute('''
            query {
                creativeWork(id: "%s") {
                    id,
                    title,
                    description,
                    sources {
                        title
                    }
                }
            }
        ''' % (IDObfuscator.encode(x), ))

        assert not result.errors

        assert result.data == OrderedDict([
            ('creativeWork', OrderedDict([
                ('id', IDObfuscator.encode(x)),
                ('title', x.title),
                ('description', x.description),
                ('sources', [])
            ]))
        ])

    def test_no_icon(self):
        x = factories.AbstractCreativeWorkFactory()
        source = factories.SourceFactory(icon='')
        x.sources.add(source.user)

        # Have to use % formats because of {}s everywhere
        result = schema.execute('''
            query {
                creativeWork(id: "%s") {
                    id,
                    title,
                    description,
                    sources {
                        title
                    }
                }
            }
        ''' % (IDObfuscator.encode(x), ))

        assert not result.errors

        assert result.data == OrderedDict([
            ('creativeWork', OrderedDict([
                ('id', IDObfuscator.encode(x)),
                ('title', x.title),
                ('description', x.description),
                ('sources', [])
            ]))
        ])
