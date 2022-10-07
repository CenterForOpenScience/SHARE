import xmltodict

from share.legacy_normalize.transform.chain import *  # noqa


EXAMPLE = '''
 <entry>
    <id>http://arxiv.org/abs/cond-mat/0102536v1</id>
    <updated>2001-02-28T20:12:09Z</updated>
    <published>2001-02-28T20:12:09Z</published>
    <title>Impact of Electron-Electron Cusp
    on Configuration Interaction Energies</title>
    <summary>  The effect of the electron-electron cusp on the convergence of configuration
interaction (CI) wave functions is examined. By analogy with the
pseudopotential approach for electron-ion interactions, an effective
electron-electron interaction is developed which closely reproduces the
scattering of the Coulomb interaction but is smooth and finite at zero
electron-electron separation. The exact many-electron wave function for this
smooth effective interaction has no cusp at zero electron-electron separation.
We perform CI and quantum Monte Carlo calculations for He and Be atoms, both
with the Coulomb electron-electron interaction and with the smooth effective
electron-electron interaction. We find that convergence of the CI expansion of
the wave function for the smooth electron-electron interaction is not
significantly improved compared with that for the divergent Coulomb interaction
for energy differences on the order of 1 mHartree. This shows that, contrary to
popular belief, description of the electron-electron cusp is not a limiting
factor, to within chemical accuracy, for CI calculations.
</summary>
    <author>
      <name>David Prendergast</name>
      <arxiv:affiliation xmlns:arxiv="http://arxiv.org/schemas/atom">Department of Physics</arxiv:affiliation>
    </author>
    <author>
      <name>M. Nolan</name>
      <arxiv:affiliation xmlns:arxiv="http://arxiv.org/schemas/atom">NMRC, University College, Cork, Ireland</arxiv:affiliation>
    </author>
    <author>
      <name>Claudia Filippi</name>
      <arxiv:affiliation xmlns:arxiv="http://arxiv.org/schemas/atom">Department of Physics</arxiv:affiliation>
    </author>
    <author>
      <name>Stephen Fahy</name>
      <arxiv:affiliation xmlns:arxiv="http://arxiv.org/schemas/atom">Department of Physics</arxiv:affiliation>
    </author>
    <author>
      <name>J. C. Greer</name>
      <arxiv:affiliation xmlns:arxiv="http://arxiv.org/schemas/atom">NMRC, University College, Cork, Ireland</arxiv:affiliation>
    </author>
    <arxiv:doi xmlns:arxiv="http://arxiv.org/schemas/atom">10.1063/1.1383585</arxiv:doi>
    <link title="doi" href="http://dx.doi.org/10.1063/1.1383585" rel="related"/>
    <arxiv:comment xmlns:arxiv="http://arxiv.org/schemas/atom">11 pages, 6 figures, 3 tables, LaTeX209, submitted to The Journal of
  Chemical Physics</arxiv:comment>
    <arxiv:journal_ref xmlns:arxiv="http://arxiv.org/schemas/atom">J. Chem. Phys. 115, 1626 (2001)</arxiv:journal_ref>
    <link href="http://arxiv.org/abs/cond-mat/0102536v1" rel="alternate" type="text/html"/>
    <link title="pdf" href="http://arxiv.org/pdf/cond-mat/0102536v1" rel="related" type="application/pdf"/>
    <arxiv:primary_category xmlns:arxiv="http://arxiv.org/schemas/atom" term="cond-mat.str-el" scheme="http://arxiv.org/schemas/atom"/>
    <category term="cond-mat.str-el" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
'''


class Organization(Parser):
    name = ctx


class IsAffiliatedWith(Parser):
    related = Delegate(Organization, ctx)


class Person(Parser):
    related_agents = Map(Delegate(IsAffiliatedWith), ctx.affiliation)
    given_name = ParseName(ctx.name).first
    family_name = ParseName(ctx.name).last


class Creator(Parser):
    agent = Delegate(Person, ctx)


class Preprint(Parser):
    title = ctx.entry.title
    description = ctx.entry.summary
    related_agents = Map(Delegate(Creator), ctx.entry.author)

    class Extra:
        comment = ctx.entry.comment
        journal_ref = ctx.entry.journal_ref


class TestParser:

    def test_preprint_parser(self):
        parsed = Preprint(
            xmltodict.parse(
                EXAMPLE,
                process_namespaces=True,
                namespaces={
                    'http://www.w3.org/2005/Atom': None,
                    'http://arxiv.org/schemas/atom': None,
                }
            )
        ).parse()

        assert isinstance(parsed, dict)
        assert parsed['@type'] == 'preprint'
        normalized = ctx.pool[parsed]
        assert normalized['extra'] == {'comment': '11 pages, 6 figures, 3 tables, LaTeX209, submitted to The Journal of\n  Chemical Physics', 'journal_ref': 'J. Chem. Phys. 115, 1626 (2001)'}

        # no newlines, leading/trailing white space, or multiple spaces
        assert normalized['title'] == 'Impact of Electron-Electron Cusp on Configuration Interaction Energies'
        assert normalized['description'] == 'The effect of the electron-electron cusp on the convergence of configuration interaction (CI) wave functions is examined. By analogy with the pseudopotential approach for electron-ion interactions, an effective electron-electron interaction is developed which closely reproduces the scattering of the Coulomb interaction but is smooth and finite at zero electron-electron separation. The exact many-electron wave function for this smooth effective interaction has no cusp at zero electron-electron separation. We perform CI and quantum Monte Carlo calculations for He and Be atoms, both with the Coulomb electron-electron interaction and with the smooth effective electron-electron interaction. We find that convergence of the CI expansion of the wave function for the smooth electron-electron interaction is not significantly improved compared with that for the divergent Coulomb interaction for energy differences on the order of 1 mHartree. This shows that, contrary to popular belief, description of the electron-electron cusp is not a limiting factor, to within chemical accuracy, for CI calculations.'
