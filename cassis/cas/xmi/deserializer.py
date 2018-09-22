from io import StringIO

from lxml import etree

from cassis.util import CassisException
from cassis.cas.cas import Cas, Sofa, View
from cassis.typesystem.typesystem import TypeSystem


def load_from_file(path: str, typesystem=TypeSystem()) -> Cas:
    return _parse_xmi(path, typesystem)


def load_from_string(xml: str, typesystem=TypeSystem()) -> Cas:
    return _parse_xmi(StringIO(xml), typesystem)


def _parse_xmi(source, typesystem):
    # namespaces
    NS_CAS = '{http:///uima/cas.ecore}'

    TAG_CAS_NULL = NS_CAS + 'NULL'
    TAG_CAS_SOFA = NS_CAS + 'Sofa'
    TAG_CAS_VIEW = NS_CAS + 'View'

    namespaces = {}
    sofas = []
    views = []
    annotations = []

    context = etree.iterparse(source, events=('start-ns', 'end'))

    for event, elem in context:
        if event == 'start-ns':
            ns, url = elem
            namespaces[ns] = url
        elif event == 'end':
            if elem.tag == TAG_CAS_NULL:
                pass
            elif elem.tag == TAG_CAS_SOFA:
                sofa = _parse_sofa(elem)
                sofas.append(sofa)
            elif elem.tag == TAG_CAS_VIEW:
                view = _parse_view(elem)
                views.append(view)
            else:
                annotation = _parse_annotation(typesystem, elem)
                annotations.append(annotation)

            # Free already processed elements
            _clear_elem(elem)

    return Cas(namespaces, sofas, views, annotations)


def _parse_sofa(elem) -> Sofa:
    attributes = elem.attrib
    id = attributes.get('{http://www.omg.org/XMI}id', '')
    sofaNum = attributes.get('sofaNum', '')
    sofaID = attributes.get('sofaID', '')
    mimeType = attributes.get('mimeType', '')
    sofaString = attributes.get('sofaString', '')
    return Sofa(id=id, sofaNum=sofaNum, sofaID=sofaID, mimeType=mimeType, sofaString=sofaString)


def _parse_view(elem) -> View:
    attributes = elem.attrib
    sofa = attributes.get('sofa', '')
    members = [int(e) for e in attributes.get('members', '').split(' ')]
    return View(sofa=sofa, members=members)


def _parse_annotation(typesystem: TypeSystem, elem):
    # Strip the http prefix, replace / with ., remove the ecore part
    # TODO: Error checking
    typename = elem.tag[9:].replace('/', '.').replace('ecore}', '')

    AnnotationType = typesystem.get_type(typename)
    attrs = dict(elem.attrib)

    # Map the xmi:id attribute to xmiID
    attrs['xmiID'] = attrs.pop('{http://www.omg.org/XMI}id', None)
    return AnnotationType(**attrs)


def _clear_elem(elem):
    """ Frees XML nodes that already have been processed to save memory """
    elem.clear()
    while elem.getprevious() is not None:
        del elem.getparent()[0]
