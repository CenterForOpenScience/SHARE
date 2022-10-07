import pytest
from share.legacy_normalize.transform.chain.utils import contact_extract


@pytest.mark.parametrize('input_text, output_text', [
    ('Contact: Lisa Floyd-Hanna (Herbarium Curator); Becky McLemore (Collections Manager) (collections@naturalhistoryinstitute.org)', {'email': 'collections@naturalhistoryinstitute.org', 'name': 'Lisa Floyd-Hanna'}),
    ('Contact: Cassandra Leah Quave (cassandra.leah.quave@emory.edu); Tharanga Samarakoon (tsamarakoon@emory.edu)', {'email': 'cassandra.leah.quave@emory.edu', 'name': 'Cassandra Leah Quave'}),
    ('Contact: Harvey E. Ballard, Jr., Director of the Floyd Bartley Herbarium and Curator of Vascular Plants (ballardh@ohio.edu)', {'email': 'ballardh@ohio.edu', 'name': 'Harvey E. Ballard'}),
    ('Contact: Dra. María Socorro Gonzalez Elizondo (herbario_ciidir@yahoo.com.mx)', {'email': 'herbario_ciidir@yahoo.com.mx', 'name': 'Dra. María Socorro Gonzalez Elizondo'}),
    ('Contact: Patti J. Anderson, Ph.D., Botanist (Patti.Anderson@freshfromflorida.com)', {'email': 'patti.anderson@freshfromflorida.com', 'name': 'Patti J. Anderson'}),
    ('Contact: Leslie R. Goertzen / Curtis J. Hansen (goertzen@auburn.edu / hansecj@auburn.edu)', {'email': 'goertzen@auburn.edu', 'name': 'Leslie R. Goertzen'}),
    ('Contact: Teresa Mayfield (tmayfield@utep.edu) or Richard Worthington (rworthin@utep.edu) ()', {'email': 'tmayfield@utep.edu', 'name': 'Teresa Mayfield'}),
    ('Contact: Taylor-Davenport, Robin M -FS (robintaylordavenport@fs.fed.us)', {'email': 'robintaylordavenport@fs.fed.us', 'name': 'Robin Taylor-Davenport'}),
    ('Contact: Diana Hurlbut, Collection Manager, Vascular P (dhurlbut@mail.nysed.gov)', {'email': 'dhurlbut@mail.nysed.gov', 'name': 'Diana Hurlbut'}),
    ('Contact: Michael D. Windham / Layne Huiet (mdw26 at duke.edu / rlh22 at duke.edu)', {'email': 'mdw26 at duke.edu', 'name': 'Michael D. Windham'}),
    ('Contact: Melissa Islam, Head Curator (melissa.islam@botanicgardens.org)', {'email': 'melissa.islam@botanicgardens.org', 'name': 'Melissa Islam'}),
    ('Contact: Dr. Joann M Chang, Science Division Chair (joann.chang@azwestern.edu)', {'email': 'joann.chang@azwestern.edu', 'name': 'Joann Chang'}),
    ('Contact: Steffi Ickert-Bond, herbarium curator (smickertbond@alaska.edu)', {'email': 'smickertbond@alaska.edu', 'name': 'Steffi Ickert-Bond'}),
    ('Contact: Andrew Miller, Ph.D., Mycologist and Director (amiller7@illinois.edu)', {'email': 'amiller7@illinois.edu', 'name': 'Andrew Miller'}),
    ('Contact: Ellen Dean, Director; Tom Starbuck, Data (tjstarbuck@ucdavis.edu)', {'email': 'tjstarbuck@ucdavis.edu', 'name': 'Ellen Dean'}),
    ('Contact: Christopher Tyrrell, Collection Manager (tyrrell@mpm.edu)', {'email': 'tyrrell@mpm.edu', 'name': 'Christopher Tyrrell'}),
    ('Contact: Dr. Dayle Saar, Director and Curator (dsaar@murraystate.edu)', {'email': 'dsaar@murraystate.edu', 'name': 'Dayle Saar'}),
    ('Contact: Jenn Yost, Director and Assistant Professor o (jyost@calpoly.edu)', {'email': 'jyost@calpoly.edu', 'name': 'Jenn Yost'}),
    ('Contact: Dr. Zack E. Murrell, Curator (murrellze@appstate.edu)', {'email': 'murrellze@appstate.edu', 'name': 'Zack E. Murrell'}),
    ('Contact: Gordon C. Tucker, Professor & Curator (gctucker@eiu.edu)', {'email': 'gctucker@eiu.edu', 'name': 'Gordon C. Tucker'}),
    ('Contact: Dr. Travis Almquist (talmquist@benedictine.edu)', {'email': 'talmquist@benedictine.edu', 'name': 'Travis Almquist'}),
    ('Contact: Tina Ayers (tina.ayers@nau.edu) (deaver.herbarium@nau.edu)', {'email': 'tina.ayers@nau.edu', 'name': 'Tina Ayers'}),
    ('Contact: Jennifer S. Kluse, Collections Manager (jkluse@lsu.edu)', {'email': 'jkluse@lsu.edu', 'name': 'Jennifer S. Kluse'}),
    ('Contact: Janelle Burke, Ph.D. (janelle.burke@howard.edu)', {'email': 'janelle.burke@howard.edu', 'name': 'Janelle Burke'}),
    ('Contact: Erin Lonergan (erinrlonergan@fs.fed.us) and M ()', {'email': 'erinrlonergan@fs.fed.us', 'name': 'Erin Lonergan'}),
    ('Contact: Mason Brock, Collections Manager (mbrock2@my.apsu.edu)', {'email': 'mbrock2@my.apsu.edu', 'name': 'Mason Brock'}),
    ('Contact: C.F. Rick Williams, Curator (willcha2@isu.edu)', {'email': 'willcha2@isu.edu', 'name': 'C.F. Rick Williams'}),
    ('Contact: Weckesser, Wendy (wendy_weckesser@nps.gov)', {'email': 'wendy_weckesser@nps.gov', 'name': 'Wendy Weckesser'}),
    ('Contact: Dr. Johnnie L. Gentry Jr. (gentry@uark.edu)', {'email': 'gentry@uark.edu', 'name': 'Johnnie L. Gentry'}),
    ('Contact: Deborah Lewis, Curator (dlewis@iastate.edu)', {'email': 'dlewis@iastate.edu', 'name': 'Deborah Lewis'}),
    ('Contact: Robert Johnson / Leigh Johnson (bry.db@byu.edu)', {'email': 'bry.db@byu.edu', 'name': 'Robert Johnson'}),
    ('Contact: Rebecca Dolan, Director (rdolan@butler.edu)', {'email': 'rdolan@butler.edu', 'name': 'Rebecca Dolan'}),
    ('Contact: Chris Lay, Administrative Director (cml@ucsc.edu)', {'email': 'cml@ucsc.edu', 'name': 'Chris Lay'}),
    ('Contact: Patricia Fall (fall@asu.edu)', {'email': 'fall@asu.edu', 'name': 'Patricia Fall'}),
    ('Contact: (Seney@fws.gov)', {'email': 'seney@fws.gov'}),
    ('Contact: Susan Hepler ()', {'name': 'Susan Hepler'}),
    ('Contact: ()', {}),
    ('Contact:', {}),
    ('', {})
])
def test_contact_extract(input_text, output_text):
    extracted = contact_extract(input_text)
    assert extracted == output_text
