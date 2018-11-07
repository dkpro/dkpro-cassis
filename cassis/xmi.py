from io import BytesIO
from typing import IO, Union

import attr

from lxml import etree

from cassis.cas import Cas, Sofa, View
from cassis.typesystem import AnnotationBase, TypeSystem


def load_cas_from_xmi(source: Union[IO, str], typesystem: TypeSystem = TypeSystem()) -> Cas:
    """ Loads a CAS from a XMI source.

    Args:
        source: The XML source. If `source` is a string, then it is assumed to be an XML string.
            If `source` is a file-like object, then the data is read from it.
        typesystem: The type system that belongs to this CAS. If `None`, an empty type system is provided.

    Returns:
        The deserialized CAS

    """

    deserializer = CasXmiDeserializer()
    if isinstance(source, str):
        return deserializer.deserialize(BytesIO(source.encode("utf-8")), typesystem=typesystem)
    else:
        return deserializer.deserialize(source, typesystem=typesystem)


class CasXmiDeserializer:
    def deserialize(self, source: Union[IO, str], typesystem: TypeSystem):
        # namespaces
        NS_XMI = "{http://www.omg.org/XMI}"
        NS_CAS = "{http:///uima/cas.ecore}"

        TAG_XMI = NS_XMI + "XMI"
        TAG_CAS_NULL = NS_CAS + "NULL"
        TAG_CAS_SOFA = NS_CAS + "Sofa"
        TAG_CAS_VIEW = NS_CAS + "View"

        sofas = []
        views = []
        annotations = []

        context = etree.iterparse(source, events=("end", ))

        for event, elem in context:
            assert event == "end"

            if elem.tag == TAG_XMI:
                # Ignore the closing 'xmi:XMI' tag
                pass
            elif elem.tag == TAG_CAS_NULL:
                pass
            elif elem.tag == TAG_CAS_SOFA:
                sofa = self._parse_sofa(elem)
                sofas.append(sofa)
            elif elem.tag == TAG_CAS_VIEW:
                view = self._parse_view(elem)
                views.append(view)
            else:
                annotation = self._parse_annotation(typesystem, elem)
                annotations.append(annotation)

            # Free already processed elements
            self._clear_elem(elem)

        return Cas(annotations=annotations, sofas=sofas, views=views)

    def _parse_sofa(self, elem) -> Sofa:
        attributes = dict(elem.attrib)
        attributes["xmiID"] = int(attributes.pop("{http://www.omg.org/XMI}id"))
        attributes["sofaNum"] = int(attributes["sofaNum"])
        return Sofa(**attributes)

    def _parse_view(self, elem) -> View:
        attributes = elem.attrib
        sofa = int(attributes["sofa"])
        members = [int(e) for e in attributes.get("members", "").split(" ")]
        return View(sofa=sofa, members=members)

    def _parse_annotation(self, typesystem: TypeSystem, elem):
        # Strip the http prefix, replace / with ., remove the ecore part
        # TODO: Error checking
        typename = elem.tag[9:].replace("/", ".").replace("ecore}", "")

        AnnotationType = typesystem.get_type(typename)
        attributes = dict(elem.attrib)

        # Map the xmi:id attribute to xmiID
        attributes["xmiID"] = int(attributes.pop("{http://www.omg.org/XMI}id"))

        if "begin" in attributes:
            attributes["begin"] = int(attributes["begin"])

        if "end" in attributes:
            attributes["end"] = int(attributes["end"])

        if "sofa" in attributes:
            attributes["sofa"] = int(attributes["sofa"])

        return AnnotationType(**attributes)

    def _clear_elem(self, elem):
        """ Frees XML nodes that already have been processed to save memory """
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]


class CasXmiSerializer:
    _COMMON_FIELD_NAMES = {"xmiID", "sofa", "begin", "end", "type"}

    def __init__(self):
        self._nsmap = {
            "xmi": "http://www.omg.org/XMI",
            "cas": "http:///uima/cas.ecore",
        }

    def serialize(self, sink: Union[IO, str], cas: Cas, pretty_print=True):
        xmi_attrs = {"{http://www.omg.org/XMI}version": "2.0"}

        root = etree.Element(etree.QName(self._nsmap["xmi"], "XMI"), nsmap=self._nsmap, **xmi_attrs)

        self._serialize_cas_null(root)

        for annotation in cas.select_all():
            self._serialize_annotation(root, annotation)

        for sofa in cas.sofas:
            self._serialize_sofa(root, sofa)

        for view in cas.views:
            self._serialize_view(root, view)

        doc = etree.ElementTree(root)
        etree.cleanup_namespaces(doc, top_nsmap=self._nsmap)

        doc.write(sink, xml_declaration=True, pretty_print=pretty_print)

    def _serialize_cas_null(self, root: etree.Element):
        name = etree.QName(self._nsmap["cas"], "NULL")
        elem = etree.SubElement(root, name)

        elem.attrib["{http://www.omg.org/XMI}id"] = "0"

    def _serialize_annotation(self, root: etree.Element, annotation: AnnotationBase):
        # The type name is a Java package, e.g. `org.myproj.Foo`.
        parts = annotation.type.split(".")

        # The cas prefix is the last component of the CAS namespace, which is the second to last
        # element of the type (the last part is the type name without package name), e.g. `myproj`
        prefix = parts[-2]
        typename = parts[-1]

        # If the prefix has not been seen yet, compute the namespace from the type name and add it
        if prefix not in self._nsmap:
            # The CAS type namespace is converted to an XML namespace URI by the following rule:
            # replace all dots with slashes, prepend http:///, and append .ecore.
            url = 'http:///' + '/'.join(parts[:-1]) + '.ecore'
            self._nsmap[prefix] = url

        name = etree.QName(self._nsmap[prefix], typename)
        elem = etree.SubElement(root, name)

        # Serialize common attributes
        elem.attrib["{http://www.omg.org/XMI}id"] = str(annotation.xmiID)
        elem.attrib["sofa"] = str(annotation.sofa)
        elem.attrib["begin"] = str(annotation.begin)
        elem.attrib["end"] = str(annotation.end)

        # Serialize feature attributes
        fields = attr.fields_dict(annotation.__class__)
        for field_name in fields:
            if field_name not in CasXmiSerializer._COMMON_FIELD_NAMES:
                # Skip over 'None' features
                value = getattr(annotation, field_name)
                if value:
                    elem.attrib[field_name] = str(value)

    def _serialize_sofa(self, root: etree.Element, sofa: Sofa):
        name = etree.QName(self._nsmap["cas"], "Sofa")
        elem = etree.SubElement(root, name)

        elem.attrib["{http://www.omg.org/XMI}id"] = str(sofa.xmiID)
        elem.attrib["sofaNum"] = str(sofa.sofaNum)
        elem.attrib["sofaID"] = str(sofa.sofaID)
        elem.attrib["mimeType"] = str(sofa.mimeType)
        elem.attrib["sofaString"] = str(sofa.sofaString)

    def _serialize_view(self, root: etree.Element, view: View):
        name = etree.QName(self._nsmap["cas"], "View")
        elem = etree.SubElement(root, name)

        elem.attrib["sofa"] = str(view.sofa)
        elem.attrib["members"] = " ".join([str(x) for x in view.members])
