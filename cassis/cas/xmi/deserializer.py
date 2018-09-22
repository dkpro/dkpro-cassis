from lxml import etree

from cassis.util import CassisException
from cassis.cas.cas import Cas, Sofa, View

class XmiCasDeserializer():

    def parse(self, source):
        # namespaces
        NS_CAS = '{http:///uima/cas.ecore}'

        TAG_CAS_NULL = NS_CAS + 'NULL'
        TAG_CAS_SOFA = NS_CAS + 'Sofa'
        TAG_CAS_VIEW = NS_CAS + 'View'

        namespaces = {}
        sofas = []
        views = []
        features = {}

        context = etree.iterparse(source, events=('start-ns', 'end'))

        for event, elem in context:
            if event == 'start-ns':
                ns, url = elem
                namespaces[ns] = url
            elif event == 'end':
                if elem.tag == TAG_CAS_NULL:
                    pass
                elif elem.tag == TAG_CAS_SOFA:
                    sofa = self._parse_sofa(elem)
                    sofas.append(sofa)
                elif elem.tag == TAG_CAS_VIEW:
                    view = self._parse_view(elem)
                    views.append(view)
                else:
                    pass

                # Free already processed elements
                self._clear_elem(elem)

        return Cas(namespaces, sofas, views)

    def _parse_sofa(self, elem) -> Sofa:
        attributes = elem.attrib
        id = attributes.get('{http://www.omg.org/XMI}id', '')
        sofaNum = attributes.get('sofaNum', '')
        sofaID = attributes.get('sofaID', '')
        mimeType = attributes.get('mimeType', '')
        sofaString = attributes.get('sofaString', '')
        return Sofa(id=id, sofaNum=sofaNum, sofaID=sofaID, mimeType=mimeType, sofaString=sofaString)

    def _parse_view(self, elem):
        attributes = elem.attrib
        sofa = attributes.get('sofa', '')
        members = [int(e) for e in attributes.get('members', '').split(' ')]
        return View(sofa=sofa, members=members)

    def _clear_elem(self, elem):
        """ Removes XML nodes that already have been processed to save memory """
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]
