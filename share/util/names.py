
def build_name_from_parts(agent_node):
    """construct some name from parts, making wild cultural assumptions

    @param agent_node: share.util.graph.MutableNode with concrete type 'abstractagent'
    @returns string (possibly empty)
    """
    # filter out falsy parts
    name_parts = filter(None, [
        agent_node['given_name'],
        agent_node['additional_name'],
        agent_node['family_name'],
        agent_node['suffix'],
    ])
    return ' '.join(name_parts).strip()


def get_related_agent_name(relation_node):
    """get the name to refer to a related agent

    @param relation_node: share.util.graph.MutableNode with concrete type 'abstractagentworkrelation'
    @returns string (possibly empty)
    """
    return (
        relation_node['cited_as']
        or relation_node['agent']['name']
        or build_name_from_parts(relation_node['agent'])
    )
