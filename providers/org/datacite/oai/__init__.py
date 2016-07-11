default_app_config = 'providers.org.datacite.oai.apps.AppConfig'

"""
Example Record Deleted

<record>
    <header status="deleted">
        <identifier>oai:oai.datacite.org:25469</identifier>
        <datestamp>2011-04-04T23:45:12Z</datestamp><
        setSpec>ANDS</setSpec><setSpec>ANDS.TEST</setSpec>
    </header>
</record>
"""

"""
Example Record

<record>
    <header>
        <identifier>oai:oai.datacite.org:32153</identifier>
        <datestamp>2011-06-08T08:57:11Z</datestamp>
        <setSpec>TIB</setSpec>
        <setSpec>TIB.WDCC</setSpec>
    </header>
    <metadata>
        <oai_datacite xmlns="http://schema.datacite.org/oai/oai-1.0/"
            xsi:schemaLocation="http://schema.datacite.org/oai/oai-1.0/
            http://schema.datacite.org/oai/oai-1.0/oai.xsd">
                <isReferenceQuality>false</isReferenceQuality>
                <schemaVersion>2.1</schemaVersion>
                <datacentreSymbol>TIB.WDCC</datacentreSymbol>
                <payload>
                    <resource xmlns="http://datacite.org/schema/kernel-2.1"
                        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                        xsi:schemaLocation="http://datacite.org/schema/kernel-2.1
                        http://schema.datacite.org/meta/kernel-2.1/metadata.xsd">
                            <identifier identifierType="DOI">10.1594/WDCC/CLM_C20_3_D3</identifier>
                            <creators>
                                <creator>
                                    <creatorName>Lautenschlager, Michael</creatorName>
                                </creator>
                                <creator>
                                    <creatorName>Keuler, Klaus</creatorName>
                                </creator>
                                <creator>
                                    <creatorName>Wunram, Claudia</creatorName>
                                </creator>
                                <creator>
                                    <creatorName>Keup-Thiel, Elke</creatorName>
                                </creator>
                                <creator>
                                    <creatorName>Schubert, Martina</creatorName>
                                </creator>
                                <creator>
                                    <creatorName>Will, Andreas</creatorName>
                                </creator>
                                <creator>
                                    <creatorName>Rockel, Burkhardt</creatorName>
                                </creator>
                                <creator>
                                    <creatorName>Boehm, Uwe</creatorName>
                                </creator>
                            </creators>
                            <titles>
                                <title>
                                    Climate Simulation with CLM, Climate of the 20th Century run
                                    no.3, Data Stream 3: European region MPI-M/MaD
                                </title>
                            </titles>
                            <publisher>World Data Center for Climate (WDCC)</publisher>
                            <publicationYear>2011</publicationYear>
                            <subjects>
                                <subject>Climate</subject>
                            </subjects>
                            <contributors>
                                <contributor contributorType="ContactPerson">
                                    <contributorName>Lautenschlager, Michael</contributorName>
                                </contributor>
                            </contributors>
                            <dates>
                                <date dateType="Created">2007-07-04</date>
                            </dates>
                            <language>eng</language>
                            <resourceType resourceTypeGeneral="Dataset">Digital</resourceType>
                            <alternateIdentifiers>
                                <alternateIdentifier alternateIdentifierType="URN">
                                    nbn:de:tib-10.1594/WDCC/CLM_C20_3_D36
                                </alternateIdentifier>
                            </alternateIdentifiers>
                            <sizes>
                                <size>2302106804800 Bytes</size>
                            </sizes>
                            <formats>
                                <format>NetCDF</format>
                            </formats>
                            <version>1</version>
                            <rights>Open access data at least for academic use.</rights>
                            <descriptions>
                                <description descriptionType="Abstract">Project: CLM regional climate
                                    model runs forced by the global IPCC scenario runs
                                    These regional climate simulations have been funded by the BMBF
                                    and computed at DKRZ by the group "Model and Data" of MPI-M, Hamburg,
                                    in close cooperation with BTU Cottbus, GKSS Geesthacht and PIK Potsdam.
                                    Serving as community model, the climate version of the local model
                                    (CLM) of the DWD was used to simulate the regional climate of the
                                    20th century (1960-2000) and 21st century (2001-2100) in Europe.
                                    The regional model runs are forced by the global IPCC scenario runs
                                    (http://www.grida.no/climate/ipcc/emission/index.htm ) to explore
                                    future developments in the European climate on a regional scale.
                                    CLM (see http://clm.gkss.de ) was run in non hydrostatic mode with
                                    0.165 degree horizontal grid resolution and was forced 6 hourly by
                                    the output of the global climate model runs with ECHAM5/MPIOM. The
                                    climate of the 20th century was simulated by three 20th century
                                    realization runs, set off at different initialization times. The
                                    climate of the 21st century was modeled with respect to two I
                                    PCC-climate scenarios (A1B and B1) with different assumptions regarding
                                    the development of global greenhouse gas concentrations.
                                    For storage in and download from this data base, the data has been
                                    transformed into time series of single model variables and is
                                    provided in two different data streams (referenced as "data stream
                                    2" and "data stream 3"). Data stream 2 is given on a rotated grid
                                    with 0.165 deg. spatial resolution (rotated coordinates). Data
                                    stream 3 is projected onto a non-rotated grid with 0.2 deg. spatial
                                    resolution (usual geographical coordinates). For the data transformation
                                    between the respective grids the cdo-routines have been used.
                                    For the original model output (referenced as "data stream 0" and
                                    "data stream 1") please contact model(at)dkrz.de for further information.
                                    See http://sga.wdc-climate.de for more details on CLM simulations
                                    in the context of the BMBF funding priority "klimazwei", some useful
                                    information on handling climate model data and the data access regulations.
                                    Summary: The experiment CLM_C20_3_D3 contains European regional
                                    climate simulations of the years 1960-2000 on a regular geographical
                                    grid. The data are generated during post processing of the corresponding
                                    data stream 2 experiment (CLM_C20_3_D2) of regional climate model runs
                                    (CLM non hydrostatic, see http://clm.gkss.de ). The simulations of
                                    the 20th century (1960-2000) have been forced by the third (_3_)
                                    run of the global 20th century climate (EH5-T63L31_OM-GR1.5L40_20C_3_6H)
                                    with observed anthropogenic forcing.
                                    In data stream 3 (_D3) the output variables of CLM data stream 2
                                    and some additionally derived parameters are stored as time series
                                    on a regular grid with a horizontal spacing of 0.2 degree. The model
                                    parameters have been transformed onto the regular geographical grid
                                    by the CDO routines. Please note, that none of the variables has
                                    been corrected for topographical differences between the two grids.
                                    The model domain of data stream 3 covers the European region starting
                                    at 34.6/-10.6 (lat/lon, centre of lower left grid box) with an
                                    increment of 0.2 degree. The number of grid points is 177/238 (lat/lon).
                                    For some model variables and additionally derived parameters some
                                    statistics on daily, monthly or yearly basis are available. See
                                    also http://sga.wdc-climate.de for a list of available parameters.
                                    Please contact sga"at"dkrz.de for data request details.
                                    See http://sga.wdc-climate.de for more details on CLM simulations
                                    in the context of the BMBF funding priority "klimazwei", some useful
                                    information on handling climate model data and the data access regulations.
                                    The output format is netCDF
                                    Experiment with CLM 2.4.11 on NEC-SX6(hurrikan)
                                    raw data: hpss:/dxul/ut/k/k204095/prism/experiments/C20_3
                                </description>
                            </descriptions>
                        </resource>
            </payload>
        </oai_datacite>
    </metadata>
</record>
"""
