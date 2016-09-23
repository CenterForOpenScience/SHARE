from share.normalize import ctx, tools
from share.normalize.parsers import Parser
from share.normalize.utils import format_address


class Link(Parser):
    url = tools.RunPython('format_link', ctx.URL)
    type = tools.RunPython('get_link_type', ctx.URL)

    class Extra:
        description = tools.Maybe(ctx, 'Description')
        url_content_type = tools.Maybe(ctx.URL_Content_Type, 'Type')

    def get_link_type(self, link):
        if 'dx.doi.org' in link:
            return 'doi'
        if self.config.home_page and self.config.home_page in link:
            return 'provider'
        return 'misc'

    def format_link(self, link):
        link_type = self.get_link_type(link)
        if link_type == 'doi':
            return tools.DOI().execute(link)
        return link


class ThroughLinks(Parser):
    link = tools.Delegate(Link, ctx)


class Person(Parser):
    suffix = tools.ParseName(
        tools.RunPython('combine_first_last_name', ctx)
    ).suffix
    family_name = tools.ParseName(
        tools.RunPython('combine_first_last_name', ctx)
    ).last
    given_name = tools.ParseName(
        tools.RunPython('combine_first_last_name', ctx)
    ).first
    additional_name = tools.ParseName(
        tools.RunPython('combine_first_last_name', ctx)
    ).middle
    location = tools.RunPython('get_address', ctx['Contact_Address'])

    class Extra:
        role = tools.Maybe(ctx, 'Role')

    def combine_first_last_name(self, ctx):
        return ctx['First_Name'] + ' ' + ctx['Last_Name']

    def get_address(self, ctx):
        address = ctx['Address']
        if isinstance(address, list):
            address1 = address[0]
            address2 = address[1]
            return format_address(
                self,
                address1=address1,
                address2=address2,
                city=ctx['City'],
                state_or_province=ctx['Province_or_State'],
                postal_code=ctx['Postal_Code'],
                country=ctx['Country']
            )

        return format_address(
            self,
            address1=ctx['Address'],
            address2=address2,
            city=ctx['City'],
            state_or_province=ctx['Province_or_State'],
            postal_code=ctx['Postal_Code'],
            country=ctx['Country']
        )


class Affiliation(Parser):
    person = tools.Delegate(Person, ctx)


class Publisher(Parser):
    name = ctx


class Organization(Parser):
    ORGANIZATION_KEYWORDS = (
        'the',
        'center'
    )

    name = tools.RunPython('combine_name', ctx)
    url = tools.Maybe(ctx, 'Data_Center_URL')
    # TODO: handle when personnel are organizations
    affiliations = tools.Map(
        tools.Delegate(Affiliation),
        tools.RunPython(
            'get_personnel',
            tools.Maybe(ctx, 'Personnel'),
            'person'
        )
    )

    def combine_name(self, ctx):
        return ctx['Data_Center_Name']['Short_Name'] + ' ' + ctx['Data_Center_Name']['Long_Name']

    def get_personnel(self, options, entity):
        """
        Returns list based on entity type.
        """
        if not isinstance(options, list):
            options = [options]

        if entity == 'person':
            people = [
                value for value in options if
                (
                    not self.list_in_string(value['First_Name'], self.ORGANIZATION_KEYWORDS) and
                    not self.list_in_string(value['Last_Name'], self.ORGANIZATION_KEYWORDS)
                )
            ]
            return people
        else:
            return options

    def list_in_string(self, string, list_):
        if any(word in string.lower() for word in list_):
            return True
        return False


class Association(Parser):
    pass


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = tools.Delegate(Tag, ctx)


class CreativeWork(Parser):
    title = tools.Join(ctx.record.metadata['DIF']['Entry_Title'])
    description = tools.Maybe(ctx.record.metadata['DIF']['Summary'], 'Abstract')

    organizations = tools.Map(
        tools.Delegate(Association.using(entity=tools.Delegate(Organization))),
        tools.Maybe(ctx.record.metadata['DIF'], 'Data_Center')
    )

    tags = tools.Map(
        tools.Delegate(ThroughTags),
        tools.Maybe(ctx.record.metadata['DIF'], 'Metadata_Name'),
        tools.Maybe(ctx.record.header, 'setSpec')
    )

    links = tools.Map(
        tools.Delegate(ThroughLinks),
        tools.Maybe(ctx.record.metadata['DIF'], 'Related_URL')
    )

    date_updated = tools.ParseDate(ctx.record.header.datestamp)

    class Extra:
        entry_id = ctx.record.metadata['DIF']['Entry_ID']

        metadata_name = tools.Maybe(ctx.record.metadata['DIF'], 'Metadata_Name')

        metadata_version = tools.Maybe(ctx.record.metadata['DIF'], 'Metadata_Version')

        last_dif_revision_date = tools.Maybe(ctx.record.metadata['DIF'], 'Last_DIF_Revision_Date')

        set_spec = tools.Maybe(ctx.record.header, 'setSpec')
