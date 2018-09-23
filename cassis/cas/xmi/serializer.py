from io import BytesIO
from typing import IO

import attr

from lxml import etree

from cassis.cas.cas import Cas, Sofa, View
from cassis.typesystem.typesystem import Annotation

_COMMON_FIELD_NAMES = {'xmiID', 'sofa', 'begin', 'end', 'type'}


def save_to_file(cas: Cas, path: str):
    with open(path, 'wb') as f:
        _serialize(f, cas)


def save_to_string(cas: Cas) -> str:
    f = BytesIO()
    _serialize(f, cas)
    return f.getvalue().decode('utf-8')


def _serialize(sink: IO, cas: Cas):
    nsmap = cas.namespaces
    xmi_attrs = {
        '{http://www.omg.org/XMI}version': '2.0'
    }
    with etree.xmlfile(sink) as xf:
        with xf.element('xmi:XMI', nsmap=nsmap, **xmi_attrs):
            _serialize_cas_null(xf, nsmap)

            for annotation in cas.select_all():
                _serialize_annotation(xf, nsmap, annotation)

            for sofa in cas.sofas:
                _serialize_sofa(xf, nsmap, sofa)

            for view in cas.views:
                _serialize_view(xf, nsmap, view)


def _serialize_cas_null(xf: IO, nsmap):
    name = etree.QName(nsmap['cas'], 'NULL')
    elem = etree.Element(name, nsmap=nsmap)

    elem.attrib['{http://www.omg.org/XMI}id'] = '0'

    xf.write(elem)


def _serialize_annotation(xf: IO, nsmap, annotation: Annotation):
    # Create tag with namespace
    parts = annotation.type.split('.')
    prefix = parts[-2]
    name = etree.QName(nsmap[prefix], parts[-1])
    elem = etree.Element(name, nsmap=nsmap)

    # Serialize common attributes
    elem.attrib['{http://www.omg.org/XMI}id'] = str(annotation.xmiID)
    elem.attrib['sofa'] = str(annotation.sofa)
    elem.attrib['begin'] = str(annotation.begin)
    elem.attrib['end'] = str(annotation.end)

    # Serialize feature attributes
    fields = attr.fields_dict(annotation.__class__)
    for field_name in fields:
        if field_name not in _COMMON_FIELD_NAMES:
            elem.attrib[field_name] = str(getattr(annotation, field_name))

    xf.write(elem)


def _serialize_sofa(xf: IO, nsmap, sofa: Sofa):
    name = etree.QName(nsmap['cas'], 'Sofa')
    elem = etree.Element(name, nsmap=nsmap)

    elem.attrib['{http://www.omg.org/XMI}id'] = str(sofa.xmiID)
    elem.attrib['sofaNum'] = str(sofa.sofaNum)
    elem.attrib['sofaID'] = str(sofa.sofaID)
    elem.attrib['mimeType'] = str(sofa.mimeType)
    elem.attrib['sofaString'] = str(sofa.sofaString)

    xf.write(elem)


def _serialize_view(xf: IO, nsmap, view: View):
    name = etree.QName(nsmap['cas'], 'View')
    elem = etree.Element(name, nsmap=nsmap)

    elem.attrib['sofa'] = str(view.sofa)
    elem.attrib['members'] = ' '.join([str(x) for x in view.members])

    xf.write(elem)
