from unittest import TestCase


from trove.trovesearch.page_cursor import (
    PageCursor,
    OffsetCursor,
    ReproduciblyRandomSampleCursor,
)


class TestPageCursor(TestCase):
    def test_queryparam_round_trip(self):
        for _original_cursor in (
            PageCursor(page_size=7),
            OffsetCursor(page_size=11),
            OffsetCursor(page_size=11, start_offset=22),
            ReproduciblyRandomSampleCursor(page_size=13),
            ReproduciblyRandomSampleCursor(page_size=3, first_page_ids=['a', 'b', 'c']),
        ):
            _qp_value = _original_cursor.as_queryparam_value()
            self.assertIsInstance(_qp_value, str)
            self.assertNotEqual(_qp_value, '')
            _cursor_from_qp = PageCursor.from_queryparam_value(_qp_value)
            self.assertIsInstance(_cursor_from_qp, type(_original_cursor))
            self.assertEqual(_cursor_from_qp, _original_cursor)
