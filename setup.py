from setuptools import setup, find_packages
from share import __version__

setup(
    name='share',
    version=__version__,
    packages=find_packages(exclude=('tests*')),
    provides=[
        'share.transformers',
        'share.harvesters'
    ],
    entry_points={
        'console_scripts': [
            'sharectl = share.bin.__main__:main',
        ],
        'share.transformers': [
            'ca.lwbin = share.legacy_normalize.transformers.ca_lwbin:LWBINTransformer',
            'com.biomedcentral = share.legacy_normalize.transformers.com_biomedcentral:BioMedCentralTransformer',
            'com.dailyssrn = share.legacy_normalize.transformers.com_dailyssrn:DailySSRNTransformer',
            'com.figshare = share.legacy_normalize.transformers.com_figshare:FigshareTransformer',
            'com.figshare.v2 = share.legacy_normalize.transformers.com_figshare_v2:FigshareV2Transformer',
            'com.mendeley.data = share.legacy_normalize.transformers.com_mendeley_data:MendeleyTransformer',
            'com.peerj = share.legacy_normalize.transformers.com_peerj:PeerJTransformer',
            'com.peerj.xml = share.legacy_normalize.transformers.com_peerj_xml:PeerJXMLTransformer',
            'com.researchregistry = share.legacy_normalize.transformers.com_researchregistry:RRTransformer',
            'com.springer = share.legacy_normalize.transformers.com_springer:SpringerTransformer',
            'edu.ageconsearch = share.legacy_normalize.transformers.edu_ageconsearch:AgeconTransformer',
            'edu.gwu = share.legacy_normalize.transformers.edu_gwu:GWScholarSpaceTransformer',
            'edu.harvarddataverse = share.legacy_normalize.transformers.edu_harvarddataverse:HarvardTransformer',
            'gov.clinicaltrials = share.legacy_normalize.transformers.gov_clinicaltrials:ClinicalTrialsTransformer',
            'gov.nih = share.legacy_normalize.transformers.gov_nih:NIHTransformer',
            'gov.nsfawards = share.legacy_normalize.transformers.gov_nsfawards:NSFTransformer',
            'gov.pubmedcentral.pmc = share.legacy_normalize.transformers.gov_pubmedcentral_pmc:PMCTransformer',
            'gov.scitech = share.legacy_normalize.transformers.gov_scitech:ScitechTransformer',
            'gov.usgs = share.legacy_normalize.transformers.gov_usgs:USGSTransformer',
            'io.osf = share.legacy_normalize.transformers.io_osf:OSFTransformer',
            'io.osf.preprints = share.legacy_normalize.transformers.io_osf_preprints:PreprintTransformer',
            'io.osf.registrations = share.legacy_normalize.transformers.io_osf_registrations:OSFRegistrationsTransformer',
            'mods = share.legacy_normalize.transformers.mods:MODSTransformer',
            'oai_dc = share.legacy_normalize.transformers.oai:OAITransformer',
            'org.arxiv = share.legacy_normalize.transformers.org_arxiv:ArxivTransformer',
            'org.biorxiv = share.legacy_normalize.transformers.org_biorxiv:BiorxivTransformer',
            'org.biorxiv.rss = share.legacy_normalize.transformers.org_biorxiv_rss:BiorxivRSSTransformer',
            'org.biorxiv.html = share.legacy_normalize.transformers.org_biorxiv_html:BiorxivHTMLTransformer',
            'org.crossref = share.legacy_normalize.transformers.org_crossref:CrossrefTransformer',
            'org.datacite = share.legacy_normalize.transformers.org_datacite:DataciteTransformer',
            'org.dataone = share.legacy_normalize.transformers.org_dataone:DataoneTransformer',
            'org.elife = share.legacy_normalize.transformers.org_elife:ElifeTransformer',
            'org.engrxiv = share.legacy_normalize.transformers.org_engrxiv:EngrxivTransformer',
            'org.ncar = share.legacy_normalize.transformers.org_ncar:NCARTransformer',
            'org.neurovault = share.legacy_normalize.transformers.org_neurovault:NeurovaultTransformer',
            'org.plos = share.legacy_normalize.transformers.org_plos:PLoSTransformer',
            'org.psyarxiv = share.legacy_normalize.transformers.org_psyarxiv:PsyarxivTransformer',
            'org.socialscienceregistry = share.legacy_normalize.transformers.org_socialscienceregistry:SCTransformer',
            'org.socarxiv = share.legacy_normalize.transformers.org_socarxiv:SocarxivTransformer',
            'org.swbiodiversity = share.legacy_normalize.transformers.org_swbiodiversity:SWTransformer',
            'v1_push = share.legacy_normalize.transformers.v1_push:V1Transformer',
            'v2_push = share.legacy_normalize.transformers.v2_push:V2PushTransformer',
        ],
        'share.harvesters': [
            'ca.lwbin = share.harvesters.ca_lwbin:LWBINHarvester',
            'com.biomedcentral = share.harvesters.com_biomedcentral:BiomedCentralHarvester',
            'com.figshare = share.harvesters.com_figshare:FigshareHarvester',
            'com.figshare.v2 = share.harvesters.com_figshare_v2:FigshareHarvester',
            'com.mendeley.data = share.harvesters.com_mendeley_data:MendeleyHarvester',
            'com.peerj = share.harvesters.com_peerj:PeerJHarvester',
            'com.researchregistry = share.harvesters.com_researchregistry:ResearchRegistryHarvester',
            'com.springer = share.harvesters.com_springer:SpringerHarvester',
            'edu.ageconsearch = share.harvesters.edu_ageconsearch:AgEconHarvester',
            'edu.gwu = share.harvesters.edu_gwu:GWScholarSpaceHarvester',
            'edu.harvarddataverse = share.harvesters.edu_harvarddataverse:HarvardDataverseHarvester',
            'gov.clinicaltrials = share.harvesters.gov_clinicaltrials:ClinicalTrialsHarvester',
            'gov.doepages = share.harvesters.gov_doepages:DoepagesHarvester',
            'gov.nih = share.harvesters.gov_nih:NIHHarvester',
            'gov.nsfawards = share.harvesters.gov_nsfawards:NSFAwardsHarvester',
            'gov.scitech = share.harvesters.gov_scitech:SciTechHarvester',
            'gov.usgs = share.harvesters.gov_usgs:USGSHarvester',
            'io.osf = share.harvesters.io_osf:OSFHarvester',
            'oai = share.harvesters.oai:OAIHarvester',
            'org.arxiv = share.harvesters.org_arxiv:ArxivHarvester',
            'org.biorxiv = share.harvesters.org_biorxiv:BiorxivHarvester',
            'org.biorxiv.rss = share.harvesters.org_biorxiv_rss:BiorxivHarvester',
            'org.biorxiv.html = share.harvesters.org_biorxiv_html:BiorxivHarvester',
            'org.crossref = share.harvesters.org_crossref:CrossRefHarvester',
            'org.dataone = share.harvesters.org_dataone:DataOneHarvester',
            'org.elife = share.harvesters.org_elife:ELifeHarvester',
            'org.ncar = share.harvesters.org_ncar:NCARHarvester',
            'org.neurovault = share.harvesters.org_neurovault:NeuroVaultHarvester',
            'org.plos = share.harvesters.org_plos:PLOSHarvester',
            'org.socialscienceregistry = share.harvesters.org_socialscienceregistry:SCHarvester',
            'org.swbiodiversity = share.harvesters.org_swbiodiversity:SWHarvester',
        ],
        'share.regulate.steps.node': [
            'cited_as = share.legacy_normalize.regulate.steps.cited_as:CitedAs',
            'trim_cycles = share.legacy_normalize.regulate.steps.trim_cycles:TrimCycles',
            'block_extra_values = share.legacy_normalize.regulate.steps.block_extra_values:BlockExtraValues',
            'normalize_agent_names = share.legacy_normalize.regulate.steps.normalize_agent_names:NormalizeAgentNames',
            'normalize_iris = share.legacy_normalize.regulate.steps.normalize_iris:NormalizeIRIs',
            'tokenize_tags = share.legacy_normalize.regulate.steps.tokenize_tags:TokenizeTags',
            'whitespace = share.legacy_normalize.regulate.steps.whitespace:StripWhitespace',
        ],
        'share.regulate.steps.graph': [
            'deduplicate = share.legacy_normalize.regulate.steps.deduplicate:Deduplicate',
        ],
        'share.regulate.steps.validate': [
            'jsonld_validator = share.legacy_normalize.regulate.steps.validate:JSONLDValidatorStep',
        ],
        'share.metadata_formats': [
            'sharev2_elastic = share.metadata_formats.sharev2_elastic:ShareV2ElasticFormatter',
            'oai_dc = share.metadata_formats.oai_dc:OaiDcFormatter',
            'turtle = share.metadata_formats.turtle:TurtleFormatter',
        ],
        'share.search.index_setup': [
            'postrend_backcompat = share.search.index_setup:PostRendBackcompatIndexSetup',
            # 'trove_v0 = share.search.index_setup:TroveV0IndexSetup',
        ],
    }
)
