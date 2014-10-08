California Polytechnic State University, San Luis Obispo
====

The [DigitalCommons@CalPoly](http://digitalcommons.calpoly.edu) shares and preserves the community's research, scholarship and campus publications. Since the material types are varied, we will have to only harvest from specific sets of records, rather than capture the whole repository. Cal Poly has provided a list of "series names" from which we should harvest.

Contact
----

Michele Wyngard and Zach Vowell at Cal Poly, content questions

Robert Allen at bepress, regarding issues with the OAI feed itself

Technical Resources
----

This will be an OAI-PMH harvest. This is a bepress institution and all the OAI feeds are provided by bepress. ([Wayne State](WayneState.md) is another bepress example.)

The OAI-PMH interface is here:
 
    http://digitalcommons.calpoly.edu/do/oai/

To see all the sets available use:

    http://digitalcommons.calpoly.edu/do/oai/?verb=ListSets

To retrieve a specific set use:

    http://digitalcommons.calpoly.edu/do/oai/?verb=ListRecords&metadataPrefix=dcq&set=publication:aerosp

The template for requests would be:

    http://digitalcommons.calpoly.edu/do/oai/?verb=[OAI-PHMVerb]&metadataPrefix=[oai_dc|qualified-dublin-core]&set=publication:[series_name]
 
_Provide any distinguishing characteristics of research outputs in your repository or sets that represent research outputs (as distinct from cultural heritage materials)._

Michele has provided a list of series to include, very similar to the [Wayne State](WayneState.md) list.

    csusymp2009
    acct_fac
    aerosp
    aero_fac
    agbsp
    agb_fac
    agedsp
    aged_fac
    ascisp
    asci_fac
    aen_fac
    arcesp
    arch_fac
    art_fac
    artsp
    bts
    bio_fac
    biosp
    bmed_fac
    bmedsp
    bae_fac
    braesp
    ccapc
    ari
    csq
    chem_fac
    chemsp
    crp_fac
    crpsp
    cenv_fac
    cadrc
    comssp
    comm_fac
    cpesp
    cscsp
    csse_fac
    cmgt_fac
    cesp
    fpe_rpt
    dscisp
    dsci_fac
    erscsp
    econ_fac
    eesp
    eeng_fac
    engl_fac
    englsp
    ethicsandanimals
    eth_fac
    essp
    fin_fac
    focus
    fsn_fac
    fsnsp
    aged_rpt
    gse_fac
    grcsp
    grc_fac
    hist_fac
    histsp
    honors
    hcssp
    hcs_fac
    imesp
    ime_fac
    it_fac
    itsp
    ir2008
    joursp
    jour_fac
    kine_fac
    kinesp
    land_fac
    laessp
    ls_fac
    lib_fac
    mgmtsp
    mgmt_sp
    mkt_fac
    theses
    matesp
    mate_fac
    math_fac
    mathsp
    mesp
    meng_fac
    mll_fac
    mllsp
    mus_fac
    musp
    nrmsp
    nrm_fac
    pres_schol
    phil_fac
    philsp
    phy_fac
    physsp
    poli_fac
    polssp
    bakerforum
    psycd_fac
    psycdsp
    rpta_fac
    rptasp
    coe_dean
    socssp
    ssci_fac
    statsp
    stat_fac
    star
    susconf
    symposium
    forum
    thdanc_fac
    wvi_fac
    wvisp

Note that this includes student works and a couple of journals not included in CrossRef.
 
Metadata Sharing Questions
----

Responses provided by Michele and Zack on 9/26/2014.

_The SHARE Notification Service will gather together research release event reports from the metadata you provide. Since we will be reusing your metadata and then retransmitting it to others as notifications, we need to be sure the rights to use that metadata are not encumbered._

_Does metadata gathering violate your terms of service?_

No. WeÕve worked with other groups who harvest our data.

_Does metadata gathering violate your privacy policy?_

No.

_Does our sharing the metadata we gather from you violate your policies?_

No. The whole IR is open access, all our metadata is openly available. Occasionally we do have students who ask us to remove their student projects. Sometimes the abstract has too much information and thatÕs what we have to remove. 

_What is the license of the metadata (for example, CC Zero)?

No. The metadata is not licensed. Essentially we have our contributors sign an agreement to allow us to display their work. 

_If unlicensed, will you explicitly license the content?_

No, not really.
