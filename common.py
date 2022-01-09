#!/usr/bin/env python3

from html.parser import HTMLParser
import requests

_UA_CHROME = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'

req_header = {
    'User-Agent': _UA_CHROME
}
sess = requests.Session()
sess.headers = req_header


class Tag():

    def __init__(self, name, attrs):
        self.name = name
        self.attrs = {}
        for key, value in attrs:
            self.attrs[key] = value

    def attr_eq(self, attr_name, attr_val):
        if attr_name not in self.attrs:
            return False
        return self.attrs[attr_name] == attr_val

    def __str__(self):
        return self.name

    def __repr__(self):
        attrs_str_list = []
        for key, value in self.attrs.items():
            attrs_str_list.append('%s="%s"' % (key, value))
        return '<%s %s>' % (self.name, ' '.join(attrs_str_list))

    def __getattr__(self, name):
        if name not in self.attrs:
            return None
        return self.attrs[name]

    def __getitem__(self, key):
        return getattr(self, key)


html_void_tags = set([
    'area', 'base', 'br', 'col', 'embed',
    'hr', 'img', 'input', 'link', 'meta',
    'param', 'source', 'track', 'wbr'])

class MyHTMLParser(HTMLParser):

    def __init__(self):
        super(MyHTMLParser, self).__init__()
        self.tags = []
        self.curr_tag = None

    def on_starttag(self, tag):
        pass

    def handle_starttag(self, tag, attrs):
        if tag in html_void_tags:
            self.handle_startendtag(tag, attrs)
        else:
            self.tags.append(Tag(tag, attrs))
            self.on_starttag(self.tags[-1])

    def on_endtag(self, tag):
        pass

    def handle_endtag(self, tag):
        self.on_endtag(self.tags[-1])
        if self.tags[-1].name == tag:
            self.tags.pop()

    def on_startendtag(self, tag):
        pass

    def handle_startendtag(self, tag, attrs):
        self.curr_tag = Tag(tag, attrs)
        self.on_startendtag(self.curr_tag)
        self.curr_tag = None

    def on_data(self, data):
        pass

    def handle_data(self, data):
        self.on_data(data)

