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
    NS_XMI = '{http://www.omg.org/XMI}'
    NS_CAS = '{http:///uima/cas.ecore}'

    TAG_XMI = NS_XMI + 'XMI'
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
            if elem.tag == TAG_XMI:
                # Ignore the closing 'xmi:XMI' tag
                pass
            elif elem.tag == TAG_CAS_NULL:
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

    return Cas(annotations=annotations, namespaces=namespaces, sofas=sofas, views=views)


def _parse_sofa(elem) -> Sofa:
    attributes = dict(elem.attrib)
    attributes['xmiID'] = int(attributes.pop('{http://www.omg.org/XMI}id'))
    return Sofa(**attributes)


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
    attributes = dict(elem.attrib)

    # Map the xmi:id attribute to xmiID
    attributes['xmiID'] = int(attributes.pop('{http://www.omg.org/XMI}id'))
    attributes['begin'] = int(attributes['begin'])
    attributes['end'] = int(attributes['end'])
    attributes['sofa'] = int(attributes['sofa'])

    return AnnotationType(**attributes)


def _clear_elem(elem):
    """ Frees XML nodes that already have been processed to save memory """
    elem.clear()
    while elem.getprevious() is not None:
        del elem.getparent()[0]
