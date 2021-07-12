import datetime as dt
import json
from decimal import Decimal

from share.models.fields import DateTimeAwareJSONEncoder, DateTimeAwareJSONDecoder


class TestDateTimeAwareJSONField:
    json_dict_data = dict(
        sample_date=dt.date.today(),
        nested_data=dict(
            sample_date=dt.date.today(),
            sample_datetime=dt.datetime.utcnow(),
            sample_decimal=Decimal("10.259")
        ),
        sample_datetime=dt.datetime.utcnow(),
        sample_decimal=Decimal("10.259"),
        sample_text='wut wut',
        list_of_things=[
            dict(
                sample_date=dt.date.today(),
                sample_datetime=dt.datetime.utcnow(),
                sample_decimal=Decimal("10.259")
            ),
            dict(
                sample_date=dt.date.today(),
                sample_datetime=dt.datetime.utcnow(),
                sample_decimal=Decimal("10.259")
            ),
            [
                dict(
                    sample_date=dt.date.today(),
                    sample_datetime=dt.datetime.utcnow(),
                    sample_decimal=Decimal("10.259")
                ),
                dict(
                    sample_date=dt.date.today(),
                    sample_datetime=dt.datetime.utcnow(),
                    sample_decimal=Decimal("10.259")
                ),
            ]
        ]
    )
    json_list_data = [
        dict(
            sample_date=dt.date.today(),
            sample_datetime=dt.datetime.utcnow(),
            sample_decimal=Decimal("10.259")
        ),
        dict(
            sample_date=dt.date.today(),
            sample_datetime=dt.datetime.utcnow(),
            sample_decimal=Decimal("10.259")
        ),
    ]

    def test_dict(self):
        json_string = json.dumps(self.json_dict_data, cls=DateTimeAwareJSONEncoder)
        json_data = json.loads(json_string, cls=DateTimeAwareJSONDecoder)
        assert json_data == self.json_dict_data, 'Nope'

    def test_list(self):
        json_string = json.dumps(self.json_list_data, cls=DateTimeAwareJSONEncoder)
        json_data = json.loads(json_string, cls=DateTimeAwareJSONDecoder)
        assert json_data == self.json_list_data, 'Nope'
