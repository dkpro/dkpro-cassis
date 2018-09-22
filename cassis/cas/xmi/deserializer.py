from lxml import etree

class XmiCasDeserializer():

    def __init__(self):
        self.namespaces = {}

    def parse_xmi(self, source):
        context = etree.iterparse(source, events=('start', 'end'))
        self._parse(context)

    def _parse(self, context):
        """

            https://www.ibm.com/developerworks/xml/library/x-hiperfparse/
        """
        for event, elem in context:
            self._handle_event(elem)

            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]
        del context

    def _handle_event(self, elem):
        print(elem.tag, elem.text)
