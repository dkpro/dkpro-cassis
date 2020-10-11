import warnings
from collections import defaultdict
from io import BytesIO
from typing import IO, Dict, Iterable, List, Set, Union

import attr
from lxml import etree

from cassis.cas import Cas, IdGenerator, Sofa, View
from cassis.typesystem import FeatureStructure, TypeNotFoundError, TypeSystem


@attr.s
class ProtoView:
    """ A view element from XMI. """

    sofa = attr.ib(validator=attr.validators.instance_of(int))  # type: int
    members = attr.ib(factory=list)  # type: List[int]


def load_cas_from_xmi(source: Union[IO, str], typesystem: TypeSystem = None, lenient: bool = False) -> Cas:
    """ Loads a CAS from a XMI source.

    Args:
        source: The XML source. If `source` is a string, then it is assumed to be an XML string.
            If `source` is a file-like object, then the data is read from it.
        typesystem: The type system that belongs to this CAS. If `None`, an empty type system is provided.
        lenient: If `True`, unknown Types will be ignored. If `False`, unknown Types will cause an exception.
            The default is `False`.

    Returns:
        The deserialized CAS

    """
    if typesystem is None:
        typesystem = TypeSystem()

    deserializer = CasXmiDeserializer()
    if isinstance(source, str):
        return deserializer.deserialize(BytesIO(source.encode("utf-8")), typesystem=typesystem, lenient=lenient)
    else:
        return deserializer.deserialize(source, typesystem=typesystem, lenient=lenient)


class CasXmiDeserializer:
    def __init__(self):
        self._max_xmi_id = 0
        self._max_sofa_num = 0

    def deserialize(self, source: Union[IO, str], typesystem: TypeSystem, lenient: bool):
        # namespaces
        NS_XMI = "{http://www.omg.org/XMI}"
        NS_CAS = "{http:///uima/cas.ecore}"

        TAG_XMI = NS_XMI + "XMI"
        TAG_CAS_SOFA = NS_CAS + "Sofa"
        TAG_CAS_VIEW = NS_CAS + "View"

        OUTSIDE_FS = 1
        INSIDE_FS = 2
        INSIDE_ARRAY = 3

        sofas = {}
        views = {}
        feature_structures = {}
        children = defaultdict(list)
        lenient_ids = set()

        context = etree.iterparse(source, events=("start", "end"))

        state = OUTSIDE_FS
        self._max_xmi_id = 0
        self._max_sofa_num = 0

        for event, elem in context:
            # Ignore the 'xmi:XMI'
            if elem.tag == TAG_XMI:
                pass
            elif elem.tag == TAG_CAS_SOFA:
                if event == "end":
                    sofa = self._parse_sofa(elem)
                    sofas[sofa.xmiID] = sofa
            elif elem.tag == TAG_CAS_VIEW:
                if event == "end":
                    proto_view = self._parse_view(elem)
                    views[proto_view.sofa] = proto_view
            else:
                """
                In XMI, array element features can be encoded as
                
                <cas:StringArray>
                    <elements>LNC</elements>
                    <elements>MTH</elements>
                    <elements>SNOMEDCT_US</elements>
                </cas:StringArray>
                
                In order to parse this with an incremental XML parser, we need to employ 
                a simple state machine. It is depicted in the following.
                            
                                   "start"               "start"
                     +-----------+-------->+-----------+-------->+--------+
                     | Outside   |         | Inside    |         | Inside |
                +--->+ feature   |         | feature   |         | array  |
                     | structure |         | structure |         | element|
                     +-----------+<--------+-----------+<--------+--------+
                                    "end"                 "end"                                
                """
                if event == "start":
                    if state == OUTSIDE_FS:
                        # We saw the opening tag of a new feature structure
                        state = INSIDE_FS
                    elif state == INSIDE_FS:
                        # We saw the opening tag of an array element
                        state = INSIDE_ARRAY
                    else:
                        raise RuntimeError("Invalid state transition: [{0}] 'start'".format(state))
                elif event == "end":
                    if state == INSIDE_FS:
                        # We saw the closing tag of a new feature
                        state = OUTSIDE_FS

                        # If a type was not found, ignore it if lenient, else raise an exception
                        try:
                            fs = self._parse_feature_structure(typesystem, elem, children)
                            feature_structures[fs.xmiID] = fs
                        except TypeNotFoundError as e:
                            if not lenient:
                                raise e

                            warnings.warn(e.message)
                            xmiID = elem.attrib.get("{http://www.omg.org/XMI}id", None)
                            if xmiID:
                                lenient_ids.add(int(xmiID))

                        children.clear()
                    elif state == INSIDE_ARRAY:
                        # We saw the closing tag of an array element
                        children[elem.tag].append(elem.text)
                        state = INSIDE_FS
                    else:
                        raise RuntimeError("Invalid state transition: [{0}] 'end'".format(state))
                else:
                    raise RuntimeError("Invalid XML event: [{0}]".format(event))

            # Free already processed elements from memory
            if event == "end":
                self._clear_elem(elem)

        # Post-process feature values
        referenced_fs = set()
        for xmi_id, fs in feature_structures.items():
            t = typesystem.get_type(fs.type)

            for feature in t.all_features:
                feature_name = feature.name

                if feature_name == "sofa":
                    value = getattr(fs, feature_name)
                    sofa = sofas[value]
                    setattr(fs, feature_name, sofa)
                    continue

                if (
                    typesystem.is_primitive(feature.rangeTypeName)
                    or typesystem.is_primitive_collection(feature.rangeTypeName)
                    or typesystem.is_primitive_collection(fs.type)
                ):
                    # TODO: Parse feature values to their real type here, e.g. parse ints or floats
                    continue

                # Resolve references here
                value = getattr(fs, feature_name)
                if value is None:
                    continue

                # Resolve references
                if typesystem.is_collection(fs.type, feature):
                    # A collection of references is a list of integers separated
                    # by single spaces, e.g. <foo:bar elements="1 2 3 42" />
                    targets = []
                    for ref in value.split():
                        target_id = int(ref)
                        target = feature_structures[target_id]
                        targets.append(target)
                        referenced_fs.add(target_id)
                    setattr(fs, feature_name, targets)
                else:
                    target_id = int(value)
                    target = feature_structures[target_id]
                    referenced_fs.add(target_id)
                    setattr(fs, feature_name, target)

        cas = Cas(typesystem=typesystem, lenient=lenient)
        for sofa in sofas.values():
            if sofa.sofaID == "_InitialView":
                view = cas.get_view("_InitialView")
            else:
                view = cas.create_view(sofa.sofaID, xmiID=sofa.xmiID, sofaNum=sofa.sofaNum)

            view.sofa_string = sofa.sofaString
            view.sofa_mime = sofa.mimeType

            # If a sofa has no members, then UIMA might omit the view. In that case,
            # we create an empty view for it.
            if sofa.xmiID in views:
                proto_view = views[sofa.xmiID]
            else:
                proto_view = ProtoView(sofa.xmiID)

            for member_id in proto_view.members:
                # We ignore ids of feature structures for which we do not have a type
                if member_id in lenient_ids:
                    continue

                fs = feature_structures[member_id]

                # Map from offsets in UIMA UTF-16 based offsets to Unicode codepoints
                if typesystem.is_instance_of(fs.type, "uima.tcas.Annotation"):
                    fs.begin = sofa._offset_converter.uima_to_cassis(fs.begin)
                    fs.end = sofa._offset_converter.uima_to_cassis(fs.end)

                view.add_annotation(fs, keep_id=True)

        cas._xmi_id_generator = IdGenerator(self._max_xmi_id + 1)
        cas._sofa_num_generator = IdGenerator(self._max_sofa_num + 1)

        return cas

    def _parse_sofa(self, elem) -> Sofa:
        attributes = dict(elem.attrib)
        attributes["xmiID"] = int(attributes.pop("{http://www.omg.org/XMI}id"))
        attributes["sofaNum"] = int(attributes["sofaNum"])
        self._max_xmi_id = max(attributes["xmiID"], self._max_xmi_id)
        self._max_sofa_num = max(attributes["sofaNum"], self._max_sofa_num)

        return Sofa(**attributes)

    def _parse_view(self, elem) -> ProtoView:
        attributes = elem.attrib
        sofa = int(attributes["sofa"])
        members = [int(e) for e in attributes.get("members", "").strip().split()]
        result = ProtoView(sofa=sofa, members=members)
        attr.validate(result)
        return result

    def _parse_feature_structure(self, typesystem: TypeSystem, elem, children: Dict[str, List[str]]):
        # Strip the http prefix, replace / with ., remove the ecore part
        # TODO: Error checking
        typename = elem.tag[9:].replace("/", ".").replace("ecore}", "").strip()

        AnnotationType = typesystem.get_type(typename)
        attributes = dict(elem.attrib)
        attributes.update(children)

        # Map the xmi:id attribute to xmiID
        attributes["xmiID"] = int(attributes.pop("{http://www.omg.org/XMI}id"))

        if "begin" in attributes:
            attributes["begin"] = int(attributes["begin"])

        if "end" in attributes:
            attributes["end"] = int(attributes["end"])

        if "sofa" in attributes:
            attributes["sofa"] = int(attributes["sofa"])

        # Remap features that use a reserved Python name
        if "self" in attributes:
            attributes["self_"] = attributes.pop("self")

        if "type" in attributes:
            attributes["type_"] = attributes.pop("type")

        self._max_xmi_id = max(attributes["xmiID"], self._max_xmi_id)
        return AnnotationType(**attributes)

    def _clear_elem(self, elem):
        """ Frees XML nodes that already have been processed to save memory """
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]


class CasXmiSerializer:
    _COMMON_FIELD_NAMES = {"xmiID", "type"}

    def __init__(self):
        self._nsmap = {"xmi": "http://www.omg.org/XMI", "cas": "http:///uima/cas.ecore"}
        self._urls_to_prefixes = {}
        self._duplicate_namespaces = defaultdict(int)

    def serialize(self, sink: Union[IO, str], cas: Cas, pretty_print=True):
        xmi_attrs = {"{http://www.omg.org/XMI}version": "2.0"}

        root = etree.Element(etree.QName(self._nsmap["xmi"], "XMI"), nsmap=self._nsmap, **xmi_attrs)

        self._serialize_cas_null(root)

        # Find all fs, even the ones that are not directly added to a sofa
        for fs in sorted(cas._find_all_fs(), key=lambda a: a.xmiID):
            self._serialize_feature_structure(cas, root, fs)

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

    def _serialize_feature_structure(self, cas: Cas, root: etree.Element, fs: FeatureStructure):
        ts = cas.typesystem

        # The type name is a Java package, e.g. `org.myproj.Foo`.
        parts = fs.type.split(".")

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
        elem.attrib["{http://www.omg.org/XMI}id"] = str(fs.xmiID)

        # Serialize feature attributes
        t = ts.get_type(fs.type)
        for feature in t.all_features:
            if feature.name in CasXmiSerializer._COMMON_FIELD_NAMES:
                continue

            feature_name = feature.name

            # Strip the underscore we added for reserved names
            if feature._has_reserved_name:
                feature_name = feature.name[:-1]

            # Skip over 'None' features
            value = getattr(fs, feature.name)
            if value is None:
                continue

            # Map back from offsets in Unicode codepoints to UIMA UTF-16 based offsets
            if ts.is_instance_of(fs.type, "uima.tcas.Annotation") and feature_name == "begin" or feature_name == "end":
                sofa: Sofa = getattr(fs, "sofa")
                value = sofa._offset_converter.cassis_to_uima(value)

            if (ts.is_instance_of(fs.type, "uima.cas.StringArray") and feature_name == "elements") or ts.is_instance_of(
                feature.rangeTypeName, "uima.cas.StringArray"
            ):
                # String arrays need to be serialized to a series of child elements, as strings can
                # contain whitespaces. Consider e.g. the array ['likes cats, 'likes dogs']. If we would
                # serialize it as an attribute, it would look like
                #
                # <my:fs elements="likes cats likes dogs" />
                #
                # which looses the information about the whitespace. Instead, we serialize it to
                #
                # <my:fs>
                #   <elements>likes cats</elements>
                #   <elements>likes dogs</elements>
                # </my:fs>
                for e in value:
                    child = etree.SubElement(elem, feature_name)
                    child.text = e
            elif feature_name == "sofa":
                elem.attrib[feature_name] = str(value.xmiID)
            elif ts.is_primitive(feature.rangeTypeName):
                elem.attrib[feature_name] = str(value)
            elif ts.is_collection(fs.type, feature):
                elements = " ".join(str(e.xmiID) for e in value)
                elem.attrib[feature_name] = elements
            else:
                # We need to encode non-primitive features as a reference
                elem.attrib[feature_name] = str(value.xmiID)

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
