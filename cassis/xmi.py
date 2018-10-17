from io import BytesIO
from typing import IO, Union

import attr

from lxml import etree

from cassis.cas import Cas, Sofa, View
from cassis.typesystem import AnnotationBase, TypeSystem


def load_cas_from_xmi(source: Union[IO, str], typesystem: TypeSystem = TypeSystem()) -> Cas:
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

        namespaces = {}
        sofas = []
        views = []
        annotations = []

        context = etree.iterparse(source, events=("start-ns", "end"))

        for event, elem in context:
            if event == "start-ns":
                ns, url = elem
                namespaces[ns] = url
            elif event == "end":
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

        return Cas(annotations=annotations, namespaces=namespaces, sofas=sofas, views=views)

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

    def serialize(self, sink: Union[IO, str], cas: Cas):
        nsmap = cas.namespaces
        xmi_attrs = {"{http://www.omg.org/XMI}version": "2.0"}
        with etree.xmlfile(sink) as xf:
            with xf.element("xmi:XMI", nsmap=nsmap, **xmi_attrs):
                self._serialize_cas_null(xf, nsmap)

                for annotation in cas.select_all():
                    self._serialize_annotation(xf, nsmap, annotation)

                for sofa in cas.sofas:
                    self._serialize_sofa(xf, nsmap, sofa)

                for view in cas.views:
                    self._serialize_view(xf, nsmap, view)

    def _serialize_cas_null(self, xf: IO, nsmap):
        name = etree.QName(nsmap["cas"], "NULL")
        elem = etree.Element(name, nsmap=nsmap)

        elem.attrib["{http://www.omg.org/XMI}id"] = "0"

        xf.write(elem)

    def _serialize_annotation(self, xf: IO, nsmap, annotation: AnnotationBase):
        # Create tag with namespace
        parts = annotation.type.split(".")
        prefix = parts[-2]
        name = etree.QName(nsmap[prefix], parts[-1])
        elem = etree.Element(name, nsmap=nsmap)

        # Serialize common attributes
        elem.attrib["{http://www.omg.org/XMI}id"] = str(annotation.xmiID)
        elem.attrib["sofa"] = str(annotation.sofa)
        elem.attrib["begin"] = str(annotation.begin)
        elem.attrib["end"] = str(annotation.end)

        # Serialize feature attributes
        fields = attr.fields_dict(annotation.__class__)
        for field_name in fields:
            if field_name not in CasXmiSerializer._COMMON_FIELD_NAMES:
                elem.attrib[field_name] = str(getattr(annotation, field_name))

        xf.write(elem)

    def _serialize_sofa(self, xf: IO, nsmap, sofa: Sofa):
        name = etree.QName(nsmap["cas"], "Sofa")
        elem = etree.Element(name, nsmap=nsmap)

        elem.attrib["{http://www.omg.org/XMI}id"] = str(sofa.xmiID)
        elem.attrib["sofaNum"] = str(sofa.sofaNum)
        elem.attrib["sofaID"] = str(sofa.sofaID)
        elem.attrib["mimeType"] = str(sofa.mimeType)
        elem.attrib["sofaString"] = str(sofa.sofaString)

        xf.write(elem)

    def _serialize_view(self, xf: IO, nsmap, view: View):
        name = etree.QName(nsmap["cas"], "View")
        elem = etree.Element(name, nsmap=nsmap)

        elem.attrib["sofa"] = str(view.sofa)
        elem.attrib["members"] = " ".join([str(x) for x in view.members])

        xf.write(elem)
