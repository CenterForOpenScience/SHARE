#!/usr/bin/env python


import requests
from HTMLParser import HTMLParser

from config import HTTP_HEADERS


def new_or_revised(pub_id):
    resp = requests.get(
        'http://eprint.iacr.org/eprint-bin/versions.pl?entry=' + pub_id,
        headers=HTTP_HEADERS
    )

    if resp.status_code != 200:
        # try again
        resp = requests.get(
            'http://eprint.iacr.org/eprint-bin/versions.pl?entry=' + pub_id,
            headers=HTTP_HEADERS
        )

    if resp.status_code != 200:
        raise Exception(
            'new_or_revised request (' + pub_id + 'error: ' + resp.status_code
            + '\n\n' + resp.text)

    if resp.text.count('posted') > 1:
        return 'revised'
    else:
        return 'new'


class EPrintParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.in_main_content = False
        self.data_type = None
        self.entry = None
        self.list_entries = []

    def feed(self, data):
        HTMLParser.feed(self, data)
        return self.list_entries

    def handle_starttag(self, tag, attrs):
        if tag == 'dl':
            self.in_main_content = True
            return

        if not self.in_main_content:
            return

        if tag == 'dt':
            if self.entry:
                self.list_entries.append(self.entry)
            self.entry = dict()
        elif tag == 'a':
            self.data_type = 'link'
        elif tag == 'b':
            self.data_type = 'title'
        elif tag == 'em':
            self.data_type = 'authors'

    def handle_endtag(self, tag):
        if tag == 'dl':
            self.in_main_content = False

            if self.entry:
                self.list_entries.append(self.entry)
                self.entry = None

            assert self.data_type is None

        elif tag in ('a', 'em', 'b'):
            self.data_type = None

    def handle_data(self, data):
        if not self.in_main_content:
            return

        if data in ('PDF', 'PS', 'PS.GZ') and self.data_type == 'link':
            self.entry['update_type'] = \
                new_or_revised(self.entry['pub_id'])
            return

        elif 'withdrawn' in data and self.data_type is None:
            self.entry['update_type'] = 'withdrawn'
            return

        if self.data_type == 'link':
            self.entry['pub_id'] = data
        elif self.data_type:
            if self.data_type in self.entry:
                self.entry[self.data_type] += data
            else:
                self.entry[self.data_type] = data

    def handle_charref(self, data):
        data = '&#' + data + ';'
        if self.data_type:
            if self.data_type in self.entry:
                self.entry[self.data_type] += HTMLParser().unescape(data)
            else:
                self.entry[self.data_type] = HTMLParser().unescape(data)


if __name__ == '__main__':
    req = requests.get(
        'http://eprint.iacr.org/eprint-bin/search.pl?last=7&title=1')
    my_parser = EPrintParser()
    entries = my_parser.feed(req.text)
    entry = entries[0]
    print type(entry['authors'])

    from pprint import pprint
    pprint(entry)
    print entry['authors']
    print
    pprint(entries)
