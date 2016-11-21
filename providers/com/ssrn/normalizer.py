from share.normalize import *  # noqa


class Link(Parser):
    url = ctx
    type = Static('provider')


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)

#TODO: split up JEL and tags
class CreativeWork(Parser):
    """

    """"""""Abstract": "Various production and services sectors which entail intensive use of labour and relatively low wages are already being undermined and downgraded to a migrant workforce by large-scale flows of migration and the fast development and expansion of globalization. Because of the various changes observed throughout the patterns of migration, the traditional conceptions and arrangements within the home and the family, along with the conventional notions of parenthood, membership, and identity, have been challenged. This chapter attempts to look into such circumstances through examining the connections between family organization and how they entail privatized care, a certain domestic setting, and the upsurge of modern and modified parenting arrangements in dealing with cross-border situations. The chapter explores how labor migration can be viewed as an intrinsic dimension of globalization and how a global care system is being formulated.",
    "Authors": {
                   "Orly  Lobel ": [
                       "https://papers.ssrn.com/sol3/cf_dev/AbsByAuth.cfm?per_id=337751",
                       "University of San Diego School of Law"
                   ]
               },
    "Citation": "Lobel, Orly, Family Geographies: Global Care Chains, Transnational Parenthood, and New Legal Challenges in an Era of Labour Globalization (2002). Law and Geography, Current Legal Issues, Vol. 5, 2002. Available at SSRN: https://ssrn.com/abstract=2870109",
    "Contacts": {
                    "Orly Lobel": " University of San Diego School of Law ( email )5998 Alcala ParkSan Diego, CA  92110-2492United StatesHOME PAGE: http://home.sandiego.edu/%7Elobel/"
                },
    "Date posted": "November 16, 2016",
    "Date revised": null,
    "ID": "2870109",
    "JEL Classification": " A00",
    "Journal": "Law and Geography, Current Legal Issues, Vol. 5, 2002",
    "Keywords": " Globalization, Migrant Workforce, Migration, Family, Parenthood, Identity, Membership, Cross-Border Situations, Global Care System",
    "Number of Pages in PDF File": " 22",
    "Title": "Family Geographies: Global Care Chains, Transnational Parenthood, and New Legal Challenges in an Era of Labour Globalization",
    "URL"
        """