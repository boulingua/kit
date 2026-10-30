"""Small HTML tree for build checks, including unquoted minified attributes."""
from html.parser import HTMLParser

VOID = frozenset('area base br col embed hr img input link meta param source track wbr'.split())


class Element:
    def __init__(self, tag, attrs=()):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []

    @property
    def classes(self):
        return set((self.attrs.get('class') or '').split())

    @property
    def text(self):
        return ''.join(c.text if isinstance(c, Element) else c for c in self.children)

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Element):
                yield from child.walk()


class TreeParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Element('document')
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        element = Element(tag, attrs)
        self.stack[-1].children.append(element)
        if tag not in VOID:
            self.stack.append(element)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def parse(html):
    parser = TreeParser()
    parser.feed(html)
    parser.close()
    return parser.root
