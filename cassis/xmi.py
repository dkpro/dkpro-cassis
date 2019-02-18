from collections import defaultdict
from io import BytesIO
from typing import IO, Union, List

import attr

from lxml import etree

from cassis.cas import Cas, Sofa, View
from cassis.typesystem import AnnotationBase, TypeSystem


@attr.s
class ProtoView:
    """ A view element from XMI. """

    sofa = attr.ib(validator=attr.validators.instance_of(int))  # type: int
    members = attr.ib(factory=list)  # type: List[int]


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
        views = {}
        annotations = {}
        elem_array = []
        ann = {}
        elements = defaultdict(list)
        fs_ids = []

        # has festure structure arrasy in snnotation
        has_parent = False

        context = etree.iterparse(source, events=("end",))

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
                proto_view = self._parse_view(elem)
                views[proto_view.sofa] = proto_view
            else:

                # nested array of features
                if elem.text is not None and elem.getparent() is not None and '{' not in elem.tag:
                    #assert len(elem.getchildren()) > 0 

                    # add new item to list as they accumulate
                    elements[elem.tag].append(elem.text)

                    # set flag for later processing of accumulated data
                    has_parent = True

                # end of annotation with nested array
                if event == "end" and '{' in elem.tag and has_parent:
                    assert elem.text is not None

                    # key is parent tag, value is feature defaultdict
                    ann[elem] = elements
                    
                    #print(annotation.xmiID)
                    annotation, _ = self._parse_annotation(typesystem, ann)
                    annotations[annotation.xmiID] = annotation

                    # clear
                    elements.clear()
                    ann.clear()
                    elem_array.clear()
                    has_parent = False

                # annotation with no nested array
                elif event == 'end' and not has_parent:
                    assert len(elem.getchildren()) == 0 

                    annotation, typename = self._parse_annotation(typesystem, elem)

                    # check for linked feature structures not in view
                    fs_id, has_fs = self._parse_feature_struct(typesystem, typename, elem)

                    if has_fs:
                        fs_ids += fs_id


                    annotations[annotation.xmiID]  = annotation

            # Free already processed elements from memory
            self._clear_elem(elem)

        if len(sofas) != len(views):
            raise RuntimeError("Number of views and sofas is not equal!")

        cas = Cas()
        for sofa in sofas:
            proto_view = views[sofa.xmiID]

            if sofa.sofaID == "_InitialView":
                view = cas.get_view("_InitialView")
            else:
                view = cas.create_view(sofa.sofaID)

            view.sofa_string = sofa.sofaString
            view.sofa_mime = sofa.mimeType

            for member_id in proto_view.members:
                annotation = annotations[member_id]
                view.add_annotation(annotation)

        for fs in fs_ids:
            annotation = annotations[fs]
            view.add_annotation(annotation)


        return cas


    def _parse_sofa(self, elem) -> Sofa:
        attributes = dict(elem.attrib)
        attributes["xmiID"] = int(attributes.pop("{http://www.omg.org/XMI}id"))
        attributes["sofaNum"] = int(attributes["sofaNum"])
        return Sofa(**attributes)


    def _parse_view(self, elem) -> ProtoView:
        attributes = elem.attrib
        sofa = int(attributes["sofa"])
        members = [int(e) for e in attributes.get("members", "").split(" ")]
        result = ProtoView(sofa=sofa, members=members)
        attr.validate(result)
        return result


    # feature structure linked to array element in an annotation, with id not in view
    def _parse_feature_struct(self, typesystem: TypeSystem, typename, elem):

        has_fs = False
        fs_id = []

        attributes = dict(elem.attrib)
        AnnotationType = typesystem.get_type(typename)

        # test for linked array
        for f in AnnotationType.all_features:
            if 'Array' in f.rangeTypeName:
                has_fs = True

                # make sure key, value exists in data and that the elementType is linked to a type system's xmi.id
                if attributes.get(f.name) and typesystem.get_type(f.elementType):
                    fs_id = [ int(i) for i in attributes[f.name].split() ]
                    pass
        
        return fs_id, has_fs


    def _parse_annotation(self, typesystem: TypeSystem, elem):
        # TODO: Error checking
       
        # dummy variable
        x = ''

        has_features = False

        # iterate through dictionary of annotation with feature array
        if isinstance(elem, dict):

            for key, value in elem.items():
                x = key
                has_features = True

        # normal annotation
        else:
            x = elem

        # Strip the http prefix, replace / with ., remove the ecore part
        typename = x.tag[9:].replace("/", ".").replace("ecore}", "")

        attributes = dict(x.attrib)

        #print(attributes)
        AnnotationType = typesystem.get_type(typename)

        # test for linked array
        for f in AnnotationType.all_features:
            if 'Array' in f.rangeTypeName:
                # make sure key, value exists in data and that the elementType is linked to a type system's xmi.id
                if attributes.get(f.name) and typesystem.get_type(f.elementType):
                    #print(typename, f.name, [ int(i) for i in attributes[f.name].split() ])
                    test_id = [ int(i) for i in attributes[f.name].split() ]
                    pass

        # not adding in "type" as it should
        if has_features:
            attributes["type"] = typename
            # add fs array elements
            for key, value in elem.items():
                for k, v in value.items():
                    attributes[k] = v

        # Map the xmi:id attribute to xmiID
        attributes["xmiID"] = int(attributes.pop("{http://www.omg.org/XMI}id"))
       
        if "begin" in attributes:
            attributes["begin"] = int(attributes["begin"])

        if "end" in attributes:
            attributes["end"] = int(attributes["end"])

        if "sofa" in attributes:
            attributes["sofa"] = int(attributes["sofa"])

        # used for linking fs to annotation; see issue #48
        if "id" in attributes:            
            attributes["id"] = int(attributes["xmiID"])

        return AnnotationType(**attributes), typename #, test_id


    def _clear_elem(self, elem):
        """ Frees XML nodes that already have been processed to save memory """
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]


class CasXmiSerializer:
    _COMMON_FIELD_NAMES = {"xmiID", "sofa", "begin", "end", "type"}

    def __init__(self):
        self._nsmap = {"xmi": "http://www.omg.org/XMI", "cas": "http:///uima/cas.ecore"}
        self._urls_to_prefixes = {}
        self._duplicate_namespaces = defaultdict(int)

    def serialize(self, sink: Union[IO, str], cas: Cas, pretty_print=True):
        xmi_attrs = {"{http://www.omg.org/XMI}version": "2.0"}

        root = etree.Element(etree.QName(self._nsmap["xmi"], "XMI"), nsmap=self._nsmap, **xmi_attrs)

        self._serialize_cas_null(root)

        for annotation in sorted(cas.select_all(), key=lambda a: a.xmiID):
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

        # The CAS type namespace is converted to an XML namespace URI by the following rule:
        # replace all dots with slashes, prepend http:///, and append .ecore.
        url = "http:///" + "/".join(parts[:-1]) + ".ecore"

        # The cas prefix is the last component of the CAS namespace, which is the second to last
        # element of the type (the last part is the type name without package name), e.g. `myproj`
        raw_prefix = parts[-2]
        typename = parts[-1]

        # If the url has not been seen yet, compute the namespace and add it
        if url not in self._urls_to_prefixes:
            # If the prefix already exists, but maps to a different url, then add it with
            # a number at the end, e.g. `type0`

            new_prefix = raw_prefix
            if raw_prefix in self._nsmap:
                suffix = self._duplicate_namespaces[raw_prefix]
                self._duplicate_namespaces[raw_prefix] += 1
                new_prefix = raw_prefix + str(suffix)

            self._nsmap[new_prefix] = url
            self._urls_to_prefixes[url] = new_prefix

        prefix = self._urls_to_prefixes[url]

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

        elem.attrib["sofa"] = str(view.sofa.xmiID)
        elem.attrib["members"] = " ".join(sorted((str(x.xmiID) for x in view.get_all_annotations()), key=int))

