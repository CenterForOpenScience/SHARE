from datetime import timedelta

import pendulum
import pytest
import requests_mock

from share.models import SourceConfig

csv_repsonse = '''
...first row is always ignored it contains the columns' titles
sample2,url2,"{last_update_date}",2017-05-02 16:17:17 -0400,2013-05-21,AEARCTR-0000005,"David James, david@gmail.com",completed,2013-01-26,2014-05-31,"[""electoral"", """"]","","abstract2",2013-03-02,2013-03-07,"information2",See pre-analysis plan.,"Treatment was randomly assigned at the group level, in a nationwide sample.","",Randomization done using Stata.,Individual,N/A,2500 individuals/1600 individuals,N/A,"MDE=5% change in perceived leakage, sd=28.8667, power=0.80, alpha=0.05",Public,This section is unavailable to the public.,,,"",,"","","",info,,"",,"","",
'''.format(last_update_date=pendulum.today().format('%B %d, %Y'))


@pytest.mark.django_db
def test_AEA_harvester():
    config = SourceConfig.objects.get(label='org.socialscienceregistry')
    url = config.harvester_kwargs['csv_url']
    harvester = config.get_harvester()

    with requests_mock.mock() as m:
        m.get(url, text=csv_repsonse)

        start = pendulum.utcnow() - timedelta(days=3)
        end = pendulum.utcnow()
        result = harvester._do_fetch(start, end)
        for data in result:
            assert data[0] == 'AEARCTR-0000005'
            assert len(data[1]['record']) == 41
