# TODO:
ways to better this mess

## better shtrove api experience

- better web-browsing experience
    - include more explanatory docs (and better fill out those explanations)
    - even more helpful (less erratic) visual design
    - in each html rendering of an api response, include a `<form>` for adding/editing/viewing query params
    - in browsable html, replace json literals with rdf rendered like the rest of the page
    - (perf) add bare-minimal IndexcardDeriver (iris, types, namelikes); use for search-result display
- better tsv/csv experience
    - set default columns for `index-value-search` (and/or broadly improve `fields` handling)
- better turtle experience
    - quoted literal graphs also turtle
    - omit unnecessary `^^rdf:string`
- better jsonld experience
    - provide `@context` (via header, at least)
    - accept jsonld at `/trove/ingest` (or at each `ldp:inbox`...)


## modular packaging
move actually-helpful logic into separate packages that can be used and maintained independently of
any particular web app/api/framework (and then use those packages in shtrove and osf)

- `osfmap`: standalone OSFMAP definition
    - define osfmap properties and shapes (following DCTAP) in static tsv files
    - use `tapshoes` (below) to generate docs and helpful utility functions 
    - may replace/simplify:
        - `osf.metadata.osf_gathering.OSFMAP` (and related constants)
        - `trove.vocab.osfmap`
        - `trove.derive.osfmap_json`
- `tapshoes`: for using and packaging [tabular application profiles](https://dcmi.github.io/dctap/) in python
    - take a set of tsv/csv files as input
        - should support any valid DCTAP (aim to be worth community interest)
        - initial/immediate use case `osfmap`
    - generate more human-readable docs of properties and shapes/types
    - validate a given record (rdf graph) against a profile
    - serialize a valid record in a consistent/stable way (according to the profile)
    - enable publishing "official" application profiles as installable python packages
    - learn from and consider using prior dctap work:
        - dctap-python: https://pypi.org/project/dctap/
            - loads tabular files into more immediately usable form
        - tap2shacl: https://pypi.org/project/tap2shacl/
            - builds shacl constraints from application profile
            - could then validate a given graph with pyshacl: https://pypi.org/project/pyshacl/
- metadata record crosswalk/serialization
    - given a record (as rdf graph) and application profile to which it conforms (like OSFMAP), offer:
        - crosswalking to a standard vocab (DCAT, schema.org, ...)
        - stable rdf serialization (json-ld, turtle, xml, ...)
        - special bespoke serialization (datacite xml/json, oai_dc, ...)
    - may replace/simplify:
        - `osf.metadata.serializers` 
        - `trove.derive`
- `shtrove`: reusable package with the good parts of share/trove
    - python api and command-line tools
    - given application profile
    - digestive tract with pluggable storage/indexing interfaces
    - methods for ingest, search, browse, subscribe
- `django-shtrove`: django wrapper for `shtrove` functionality
    - set application profile via django setting
    - django models for storage, elasticsearch for indexing
    - django views for ingest, search, browse, subscribe


## open web standards
- data catalog vocabulary (DCAT) https://www.w3.org/TR/vocab-dcat-3/
    - an appropriate (and better thought-thru) vocab for a lot of what shtrove does
    - already used in some ways, but would benefit from adopting more thoroughly
        - replace bespoke types (like `trove:Indexcard`) with better-defined dcat equivalents (like `dcat:CatalogRecord`)
        - rename various properties/types/variables similarly
            - "catalog" vs "index"
            - "record" vs "card"
        - replace checksum-iris with `spdx:checksum` (added in dcat 3)
- linked data notifications (LDN) https://www.w3.org/TR/ldn/
    - shtrove incidentally (partially) aligns with linked-data principles -- could lean into that
    - replace `/trove/ingest` with one or more `ldp:inbox` urls
    - trove index-card like an inbox containing current/past resource descriptions
        ```
        <://osf.example/blarg> ldp:inbox <://shtrove.example/index-card/0000-00...> .
        <://shtrove.example/index-card/0000-00...> ldp:contains <://shtrove.example/description/0000-00...> .
        <://shtrove.example/description/0000-00...> foaf:primaryTopic <://osf.example/blarg>
        ```
        (might consider renaming "index-card" for consistency/clarity)
