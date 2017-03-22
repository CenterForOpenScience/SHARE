from share.transform.chain import ctx, links as tools, ChainTransformer
from share.transform.chain.parsers import Parser
from share.transform.chain.utils import format_address


class WorkIdentifier(Parser):
    uri = tools.RunPython('get_ncar_identifier', ctx)

    class Extra:
        description = tools.Try(ctx.Related_URL.Description)
        url_content_type = tools.Try(ctx.Related_URL.URL_Content_Type.Type)

    def get_ncar_identifier(self, ctx):
        return 'https://www.earthsystemgrid.org/dataset/{}.html'.format(ctx['Entry_ID'])


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = tools.Delegate(Tag, ctx)


class PersonnelAgent(Parser):
    schema = tools.GuessAgentType(
        tools.RunPython('combine_first_last_name', ctx)
    )

    name = tools.RunPython('combine_first_last_name', ctx)
    location = tools.RunPython('get_address', ctx['Contact_Address'])

    class Extra:
        role = tools.Try(ctx.Role)
        url = tools.Try(ctx.Data_Center_URL)

    def combine_first_last_name(self, ctx):
        return ctx['First_Name'] + ' ' + ctx['Last_Name']

    def get_address(self, ctx):
        address = ctx['Address']
        if isinstance(address, list):
            address1 = address[0]
            address2 = address[1]
            return format_address(
                address1=address1,
                address2=address2,
                city=ctx['City'],
                state_or_province=ctx['Province_or_State'],
                postal_code=ctx['Postal_Code'],
                country=ctx['Country']
            )

        return format_address(
            address1=ctx['Address'],
            address2=address2,
            city=ctx['City'],
            state_or_province=ctx['Province_or_State'],
            postal_code=ctx['Postal_Code'],
            country=ctx['Country']
        )


class IsAffiliatedWith(Parser):
    related = tools.Delegate(PersonnelAgent, ctx)


class DataCenterAgent(Parser):
    schema = tools.GuessAgentType(
        ctx.Data_Center_Name.Long_Name,
        default='organization'
    )

    name = ctx.Data_Center_Name.Long_Name
    related_agents = tools.Map(tools.Delegate(IsAffiliatedWith), tools.Try(ctx.Personnel))

    class Extra:
        data_center_short_name = ctx.Data_Center_Name.Short_Name


class AgentWorkRelation(Parser):
    agent = tools.Delegate(DataCenterAgent, ctx)


class DataSet(Parser):
    title = tools.Join(tools.Try(ctx.record.metadata.DIF.Entry_Title))
    description = tools.Try(ctx.record.metadata.DIF.Summary.Abstract)

    related_agents = tools.Map(
        tools.Delegate(AgentWorkRelation),
        tools.Try(ctx.record.metadata.DIF.Data_Center)
    )

    tags = tools.Map(
        tools.Delegate(ThroughTags),
        tools.Try(ctx.record.metadata.DIF.Metadata_Name),
        tools.Try(ctx.record.header.setSpec)
    )

    identifiers = tools.Map(tools.Delegate(WorkIdentifier), tools.Try(ctx.record.metadata.DIF))

    date_updated = tools.ParseDate(ctx.record.header.datestamp)

    is_deleted = tools.RunPython('check_status', tools.Try(ctx.record.header['@status']))

    class Extra:
        status = tools.Try(ctx.record.header['@status'])

        entry_id = tools.Try(ctx.record.metadata.DIF.Entry_ID)

        metadata_name = tools.Try(ctx.record.metadata.DIF.Metadata_Name)

        metadata_version = tools.Try(ctx.record.metadata.DIF.Metadata_Version)

        last_dif_revision_date = tools.Try(ctx.record.metadata.DIF.Last_DIF_Revision_Date)

        set_spec = ctx.record.header.setSpec

    def check_status(self, status):
        if status == 'deleted':
            return True
        return False


class NCARTransformer(ChainTransformer):
    VERSION = 1
    root_parser = DataSet
