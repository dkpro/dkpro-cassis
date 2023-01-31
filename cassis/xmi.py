import warnings
from collections import defaultdict
from io import BytesIO
from math import isinf, isnan
from pathlib import Path
from typing import IO, Dict, List, Union

import attr
from lxml import etree

from cassis.cas import Cas, IdGenerator, Sofa, View
from cassis.typesystem import (
    _LIST_TYPES,
    _PRIMITIVE_ARRAY_TYPES,
    _PRIMITIVE_LIST_TYPES,
    FEATURE_BASE_NAME_BEGIN,
    FEATURE_BASE_NAME_END,
    FEATURE_BASE_NAME_HEAD,
    FEATURE_BASE_NAME_SOFA,
    FEATURE_BASE_NAME_TAIL,
    TYPE_NAME_ANNOTATION,
    TYPE_NAME_BOOLEAN,
    TYPE_NAME_BOOLEAN_ARRAY,
    TYPE_NAME_BYTE,
    TYPE_NAME_BYTE_ARRAY,
    TYPE_NAME_DOUBLE,
    TYPE_NAME_DOUBLE_ARRAY,
    TYPE_NAME_EMPTY_FLOAT_LIST,
    TYPE_NAME_EMPTY_FS_LIST,
    TYPE_NAME_EMPTY_INTEGER_LIST,
    TYPE_NAME_EMPTY_STRING_LIST,
    TYPE_NAME_FLOAT,
    TYPE_NAME_FLOAT_ARRAY,
    TYPE_NAME_FLOAT_LIST,
    TYPE_NAME_FS_ARRAY,
    TYPE_NAME_FS_LIST,
    TYPE_NAME_INTEGER,
    TYPE_NAME_INTEGER_ARRAY,
    TYPE_NAME_INTEGER_LIST,
    TYPE_NAME_LONG,
    TYPE_NAME_LONG_ARRAY,
    TYPE_NAME_NON_EMPTY_FLOAT_LIST,
    TYPE_NAME_NON_EMPTY_FS_LIST,
    TYPE_NAME_NON_EMPTY_INTEGER_LIST,
    TYPE_NAME_NON_EMPTY_STRING_LIST,
    TYPE_NAME_SHORT,
    TYPE_NAME_SHORT_ARRAY,
    TYPE_NAME_SOFA,
    TYPE_NAME_STRING,
    TYPE_NAME_STRING_ARRAY,
    TYPE_NAME_STRING_LIST,
    FeatureStructure,
    Type,
    TypeNotFoundError,
    TypeSystem,
)

NAN_VALUE = "NaN"
POSITIVE_INFINITE_VALUE = "Infinity"
NEGATIVE_INFINITE_VALUE = "-Infinity"


@attr.s
class ProtoView:
    """A view element from XMI."""

    sofa: int = attr.ib(validator=attr.validators.instance_of(int))
    members: List[int] = attr.ib(factory=list)


def load_cas_from_xmi(
    source: Union[IO, Path, str], typesystem: TypeSystem = None, lenient: bool = False, trusted: bool = False
) -> Cas:
    """Loads a CAS from a XMI source.

    Args:
        source: The XML source. If `source` is a string, then it is assumed to be an XML string.
            If `source` is a file-like object, then the data is read from it.
            If `source` is a `Path`, then load the file at the given location.
        typesystem: The type system that belongs to this CAS. If `None`, an empty type system is provided.
        lenient: If `True`, unknown Types will be ignored. If `False`, unknown Types will cause an exception.
            The default is `False`.
        trusted: If `True`, disables checks like XML parser security restrictions.

    Returns:
        The deserialized CAS

    """
    if typesystem is None:
        typesystem = TypeSystem()

    deserializer = CasXmiDeserializer()
    if isinstance(source, str):
        return deserializer.deserialize(
            BytesIO(source.encode("utf-8")), typesystem=typesystem, lenient=lenient, trusted=trusted
        )
    if isinstance(source, Path):
        with source.open("rb") as src:
            return deserializer.deserialize(src, typesystem=typesystem, lenient=lenient, trusted=trusted)
    else:
        return deserializer.deserialize(source, typesystem=typesystem, lenient=lenient, trusted=trusted)


class CasXmiDeserializer:
    def __init__(self):
        self._max_xmi_id = 0
        self._max_sofa_num = 0

    def deserialize(self, source: Union[IO, str], typesystem: TypeSystem, lenient: bool, trusted: bool):
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

        context = etree.iterparse(source, events=("start", "end"), huge_tree=trusted)

        state = OUTSIDE_FS
        self._max_xmi_id = 0
        self._max_sofa_num = 0

        for event, elem in context:
            # Ignore the 'xmi:XMI'
            if elem.tag == TAG_XMI:
                pass
            elif elem.tag == TAG_CAS_SOFA:
                if event == "end":
                    sofa = self._parse_sofa(typesystem, elem)
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
                        raise RuntimeError(f"Invalid state transition: [{state}] 'start'")
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
                        raise RuntimeError(f"Invalid state transition: [{state}] 'end'")
                else:
                    raise RuntimeError(f"Invalid XML event: [{event}]")

            # Free already processed elements from memory
            if event == "end":
                self._clear_elem(elem)

        # See https://github.com/dkpro/dkpro-cassis/issues/266
        # The checking for each feature if it is a StringArray is rather slow, hence, we cache the results
        is_instance_of_string_array_map = {}

        # Post-process feature values
        for xmi_id, fs in feature_structures.items():
            t = typesystem.get_type(fs.type.name)

            for feature in t.all_features:
                feature_name = feature.name
                value = fs[feature_name]

                if feature_name == "sofa":
                    fs[feature_name] = sofas[value]
                    continue

                if fs.type.name not in is_instance_of_string_array_map:
                    is_instance_of_string_array_map[fs.type.name] = typesystem.is_instance_of(
                        fs.type.name, TYPE_NAME_STRING_ARRAY
                    )

                if is_instance_of_string_array_map[fs.type.name]:
                    # We already parsed string arrays to a Python list of string
                    # before, so we do not need to work more on this
                    continue
                elif typesystem.is_primitive(feature.rangeType):
                    fs[feature_name] = self._parse_primitive_value(feature.rangeType, value)
                    continue
                elif typesystem.is_primitive_array(fs.type) and feature_name == "elements":
                    # Separately rendered arrays (typically used with multipleReferencesAllowed = True)
                    fs[feature_name] = self._parse_primitive_array(fs.type, value)
                elif typesystem.is_primitive_array(feature.rangeType) and not feature.multipleReferencesAllowed:
                    # Array feature rendered inline (multipleReferencesAllowed = False|None)
                    # We also end up here for array features that were rendered as child elements. No need to parse
                    # them again, so we check if the value is still a string (i.e. attribute value) and only then
                    # process it
                    if isinstance(value, str):
                        FSType = feature.rangeType
                        fs[feature_name] = FSType(elements=self._parse_primitive_array(feature.rangeType, value))
                elif typesystem.is_primitive_list(feature.rangeType) and not feature.multipleReferencesAllowed:
                    # Array feature rendered inline (multipleReferencesAllowed = False|None)
                    # We also end up here for array features that were rendered as child elements. No need to parse
                    # them again, so we check if the value is still a string (i.e. attribute value) and only then
                    # process it
                    if isinstance(value, str):
                        fs[feature_name] = self._parse_primitive_list(feature.rangeType, value)
                else:
                    # Resolve references here
                    if value is None:
                        continue

                    # Resolve references
                    if fs.type.name == TYPE_NAME_FS_ARRAY or (
                        feature.rangeType.name == TYPE_NAME_FS_ARRAY and not feature.multipleReferencesAllowed
                    ):
                        # An array of references is a list of integers separated
                        # by single spaces, e.g. <foo:bar elements="1 2 3 42" />
                        targets = []
                        for ref in value.split():
                            target_id = int(ref)
                            target = feature_structures[target_id]
                            targets.append(target)

                        if feature.rangeType.name == TYPE_NAME_FS_ARRAY:
                            # Wrap inline array into the appropriate array object
                            ArrayType = typesystem.get_type(TYPE_NAME_FS_ARRAY)
                            targets = ArrayType(elements=targets)

                        fs[feature_name] = targets
                    elif feature.rangeType.name == TYPE_NAME_FS_LIST and not feature.multipleReferencesAllowed:
                        # Array feature rendered inline (multipleReferencesAllowed = False|None)
                        # We also end up here for array features that were rendered as child elements. No need to parse
                        # them again, so we check if the value is still a string (i.e. attribute value) and only then
                        # process it
                        if isinstance(value, list) or isinstance(value, str):
                            fs[feature_name] = self._parse_fs_list(feature_structures, feature.rangeType, value)
                    else:
                        target_id = int(value)
                        fs[feature_name] = feature_structures[target_id]

        cas = Cas(typesystem=typesystem, lenient=lenient)
        for sofa in sofas.values():
            if sofa.sofaID == "_InitialView":
                view = cas.get_view("_InitialView")

                # We need to make sure that the sofa gets the real xmi, see #155
                view.get_sofa().xmiID = sofa.xmiID
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
                if typesystem.is_instance_of(fs.type.name, "uima.tcas.Annotation"):
                    fs.begin = sofa._offset_converter.external_to_python(fs.begin)
                    fs.end = sofa._offset_converter.external_to_python(fs.end)

                view.add(fs, keep_id=True)

        cas._xmi_id_generator = IdGenerator(self._max_xmi_id + 1)
        cas._sofa_num_generator = IdGenerator(self._max_sofa_num + 1)

        return cas

    def _parse_sofa(self, typesystem: TypeSystem, elem) -> Sofa:
        attributes = dict(elem.attrib)
        attributes["xmiID"] = int(attributes.pop("{http://www.omg.org/XMI}id"))
        attributes["sofaNum"] = int(attributes["sofaNum"])
        attributes["type"] = typesystem.get_type(TYPE_NAME_SOFA)
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
        type_name: str = elem.tag[9:].replace("/", ".").replace("ecore}", "").strip()

        if type_name.startswith("uima.noNamespace."):
            type_name = type_name[17:]

        AnnotationType = typesystem.get_type(type_name)
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

        # Arrays which were represented as nested elements in the XMI have so far have only been parsed into a Python
        # arrays. Now we convert them to proper UIMA arrays/lists
        if not typesystem.is_primitive_array(type_name):
            for feature_name, feature_value in children.items():
                feature = AnnotationType.get_feature(feature_name)
                if typesystem.is_primitive_array(feature.rangeType):
                    ArrayType = feature.rangeType
                    attributes[feature_name] = ArrayType(elements=attributes[feature_name])
                if typesystem.is_primitive_list(feature.rangeType):
                    attributes[feature_name] = self._parse_primitive_list(feature.rangeType, attributes[feature_name])

        self._max_xmi_id = max(attributes["xmiID"], self._max_xmi_id)
        return AnnotationType(**attributes)

    def _parse_primitive_list(self, type_: Type, value: Union[str, List[str]]):
        if value is None:
            return None

        # Convert the inline array into the linked NonEmptyList/EmptyList instances
        if type_.name == TYPE_NAME_INTEGER_LIST:
            EmptyList = type_.typesystem.get_type(TYPE_NAME_EMPTY_INTEGER_LIST)
            NonEmptyList = type_.typesystem.get_type(TYPE_NAME_NON_EMPTY_INTEGER_LIST)
            conv = int
        elif type_.name == TYPE_NAME_FLOAT_LIST:
            EmptyList = type_.typesystem.get_type(TYPE_NAME_EMPTY_FLOAT_LIST)
            NonEmptyList = type_.typesystem.get_type(TYPE_NAME_NON_EMPTY_FLOAT_LIST)
            conv = float
        elif type_.name == TYPE_NAME_STRING_LIST:
            EmptyList = type_.typesystem.get_type(TYPE_NAME_EMPTY_STRING_LIST)
            NonEmptyList = type_.typesystem.get_type(TYPE_NAME_NON_EMPTY_STRING_LIST)
            conv = str
        else:
            raise ValueError(f"Unexpected primitive list type: {type_.name}")

        elements = value.split() if isinstance(value, str) else value

        head = EmptyList()
        for e in reversed(elements):
            tail = head
            head = NonEmptyList()
            head.set(FEATURE_BASE_NAME_HEAD, conv(e))
            head.set(FEATURE_BASE_NAME_TAIL, tail)
        return head

    def _parse_fs_list(self, feature_structures, type_: Type, value: str):
        # Convert the inline array into the linked NonEmptyFSList/EmptyFSList instances
        NonEmptyFSList = type_.typesystem.get_type(TYPE_NAME_NON_EMPTY_FS_LIST)
        EmptyFSList = type_.typesystem.get_type(TYPE_NAME_EMPTY_FS_LIST)

        elements = value.split() if isinstance(value, str) else value

        head = EmptyFSList()
        for e in reversed(elements):
            tail = head
            head = NonEmptyFSList()
            head.set(FEATURE_BASE_NAME_HEAD, feature_structures[int(e)])
            head.set(FEATURE_BASE_NAME_TAIL, tail)
        return head

    def _parse_primitive_array(self, type_: Type, value: Union[str, List[str]]) -> List:
        """Primitive collections are serialized as white space separated primitive values"""

        if value is None:
            return None

        # TODO: Use type name global variable here instead of hardcoded string literal
        elements = value.split() if isinstance(value, str) else value

        type_name = type_.name
        if type_name in [TYPE_NAME_FLOAT_ARRAY, TYPE_NAME_DOUBLE_ARRAY]:
            return [float(e) for e in elements] if value else []
        elif type_name in [TYPE_NAME_INTEGER_ARRAY, TYPE_NAME_SHORT_ARRAY, TYPE_NAME_LONG_ARRAY]:
            return [int(e) for e in elements] if value else []
        elif type_name == TYPE_NAME_STRING_ARRAY:
            if elements:
                raise ValueError(f"String array values must be provided as nested elements: {elements}")
            return []
        elif type_name == TYPE_NAME_BOOLEAN_ARRAY:
            return [self._parse_bool(e) for e in elements] if value else []
        elif type_name == TYPE_NAME_BYTE_ARRAY:
            return list(bytearray.fromhex(value)) if value else []
        else:
            raise ValueError(f"Not a primitive collection type: {type_name}")

    def _parse_primitive_value(self, type_: Type, value: str) -> Union[float, int, bool, str, None]:
        type_name = type_.name
        if value is None:
            return None
        elif type_name == TYPE_NAME_STRING:
            return value
        elif type_name in [TYPE_NAME_FLOAT, TYPE_NAME_DOUBLE]:
            return float(value)
        elif type_name in [TYPE_NAME_INTEGER, TYPE_NAME_SHORT, TYPE_NAME_LONG, TYPE_NAME_BYTE]:
            return int(value)
        elif type_name == TYPE_NAME_BOOLEAN:
            return self._parse_bool(value)
        else:
            raise ValueError(f"Not a primitive type: {type_name}")

    def _parse_bool(self, s: str) -> bool:
        if s == "true":
            return True
        if s == "false":
            return False
        raise ValueError(f"Not a boolean: {s}")

    def _clear_elem(self, elem):
        """Frees XML nodes that already have been processed to save memory"""
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]


class CasXmiSerializer:
    _COMMON_FIELD_NAMES = {"xmiID", "type"}

    def __init__(self):
        self._nsmap = {"xmi": "http://www.omg.org/XMI", "cas": "http:///uima/cas.ecore"}
        self._urls_to_prefixes = {}
        self._duplicate_namespaces = defaultdict(int)

    def serialize(self, sink: Union[IO, str, None], cas: Cas, pretty_print=True) -> Union[str, None]:
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

        return_str = sink is None
        if return_str:
            sink = BytesIO()

        doc.write(sink, xml_declaration=True, pretty_print=pretty_print, encoding="UTF-8")

        if return_str:
            return sink.getvalue().decode("utf-8")

        return None

    def _serialize_cas_null(self, root: etree.Element):
        name = etree.QName(self._nsmap["cas"], "NULL")
        elem = etree.SubElement(root, name)

        elem.attrib["{http://www.omg.org/XMI}id"] = "0"

    def _serialize_feature_structure(self, cas: Cas, root: etree.Element, fs: FeatureStructure):
        ts = cas.typesystem

        type_name = fs.type.name
        if "." not in type_name:
            type_name = f"uima.noNamespace.{type_name}"

        # The type name is a Java package, e.g. `org.myproj.Foo`.
        parts = type_name.split(".")

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

        # Case where arrays are rendered as separate elements (not inline) for use with multipleReferencesAllowed = True
        if ts.is_primitive_array(fs.type.name) or fs.type.name == "uima.cas.FSArray":
            if fs.elements is None:
                return
            elif ts.is_instance_of(fs.type.name, "uima.cas.StringArray"):
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
                for e in fs.elements:
                    child = etree.SubElement(elem, "elements")
                    child.text = e
            elif fs.type.name == "uima.cas.FSArray":
                elements = " ".join(str(e.xmiID) for e in fs.elements)
                elem.attrib["elements"] = elements
            else:
                elem.attrib["elements"] = self._serialize_primitive_array(fs.type.name, fs.elements)
            return

        # Serialize feature attributes
        t = fs.type
        for feature in t.all_features:
            if feature.name in CasXmiSerializer._COMMON_FIELD_NAMES:
                continue

            feature_name = feature.name

            # Strip the underscore we added for reserved names
            if feature._has_reserved_name:
                feature_name = feature.name[:-1]

            # Skip over 'None' features
            value = fs[feature.name]
            if value is None:
                continue

            # Map back from offsets in Unicode codepoints to UIMA UTF-16 based offsets
            if (
                ts.is_instance_of(fs.type.name, TYPE_NAME_ANNOTATION)
                and feature_name == FEATURE_BASE_NAME_BEGIN
                or feature_name == FEATURE_BASE_NAME_END
            ):
                sofa: Sofa = fs.sofa
                value = sofa._offset_converter.python_to_external(value)

            if ts.is_instance_of(feature.rangeType, TYPE_NAME_STRING_ARRAY) and not feature.multipleReferencesAllowed:
                if value.elements is not None:  # Compare to none as not to skip if elements is empty!
                    if not value.elements:
                        elem.attrib[feature_name] = ""
                    else:
                        for e in value.elements:
                            child = etree.SubElement(elem, feature_name)
                            child.text = e
            elif ts.is_instance_of(feature.rangeType, TYPE_NAME_STRING_LIST) and not feature.multipleReferencesAllowed:
                if value is not None:  # Compare to none to not skip if elements is empty!
                    for e in self._collect_list_elements(feature.rangeType.name, value):
                        child = etree.SubElement(elem, feature_name)
                        child.text = e
            elif ts.is_primitive_array(feature.rangeType) and not feature.multipleReferencesAllowed:
                if value.elements is not None:  # Compare to none to not skip if elements is empty!
                    elem.attrib[feature_name] = self._serialize_primitive_array(feature.rangeType.name, value.elements)
            elif ts.is_primitive_list(feature.rangeType) and not feature.multipleReferencesAllowed:
                if value is not None:  # Compare to none to not skip if elements is empty!
                    elem.attrib[feature_name] = self._serialize_primitive_list(feature.rangeType.name, value)
            elif feature.rangeType.name == TYPE_NAME_FS_ARRAY and not feature.multipleReferencesAllowed:
                if value.elements is not None:  # Compare to none to not skip if elements is empty!
                    elem.attrib[feature_name] = " ".join(str(e.xmiID) for e in value.elements)
            elif feature.rangeType.name == TYPE_NAME_FS_LIST and not feature.multipleReferencesAllowed:
                if value is not None:  # Compare to none to not skip if elements is empty!
                    elem.attrib[feature_name] = " ".join(
                        str(e.xmiID) for e in self._collect_list_elements(feature.rangeType.name, value)
                    )
            elif feature_name == FEATURE_BASE_NAME_SOFA:
                elem.attrib[feature_name] = str(value.xmiID)
            elif feature.rangeType.name == TYPE_NAME_BOOLEAN:
                elem.attrib[feature_name] = "true" if value else "false"
            elif feature.rangeType.name in {TYPE_NAME_DOUBLE, TYPE_NAME_FLOAT}:
                elem.attrib[feature_name] = self._serialize_float_value(value)
            elif ts.is_primitive(feature.rangeType):
                elem.attrib[feature_name] = str(value)
            else:
                # We need to encode non-primitive features as a reference
                elem.attrib[feature_name] = str(value.xmiID)

    def _serialize_sofa(self, root: etree.Element, sofa: Sofa):
        name = etree.QName(self._nsmap["cas"], "Sofa")
        elem = etree.SubElement(root, name)

        elem.attrib["{http://www.omg.org/XMI}id"] = str(sofa.xmiID)
        elem.attrib["sofaNum"] = str(sofa.sofaNum)
        elem.attrib["sofaID"] = str(sofa.sofaID)
        if sofa.mimeType is not None:
            elem.attrib["mimeType"] = str(sofa.mimeType)
        if sofa.sofaString is not None:
            elem.attrib["sofaString"] = str(sofa.sofaString)

    def _serialize_view(self, root: etree.Element, view: View):
        name = etree.QName(self._nsmap["cas"], "View")
        elem = etree.SubElement(root, name)

        elem.attrib["sofa"] = str(view.sofa.xmiID)
        elem.attrib["members"] = " ".join(sorted((str(x.xmiID) for x in view.get_all_annotations()), key=int))

    def _collect_list_elements(self, type_name: str, value) -> List[str]:
        if type_name not in _LIST_TYPES:
            raise ValueError(f"Not a primitive list: {type_name}")

        elements = []
        current = value
        while hasattr(current, "head"):
            elements.append(current.head)
            current = current.tail
        return elements

    def _serialize_primitive_list(self, type_name: str, value) -> str:
        elements = []
        for e in self._collect_list_elements(type_name, value):
            if isinstance(e, float):
                elements.append(self._serialize_float_value(e))
            else:
                elements.append(str(e))
        return " ".join(elements)

    def _serialize_primitive_array(self, type_name: str, values: List) -> str:
        """Primitive collections are serialized as white space seperated primitive values"""

        # TODO: Use type name global variable here instead of hardcoded string literal
        if type_name not in _PRIMITIVE_ARRAY_TYPES:
            raise ValueError(f"Not a primitive array: {type_name}")

        if type_name == TYPE_NAME_BOOLEAN_ARRAY:
            return " ".join(str(e).lower() for e in values)
        elif type_name == TYPE_NAME_BYTE_ARRAY:
            return "".join(f"{x:02X}" for x in values)
        elif type_name in {TYPE_NAME_DOUBLE_ARRAY, TYPE_NAME_FLOAT_ARRAY}:
            return " ".join(self._serialize_float_value(x) for x in values)
        else:
            return " ".join(str(e) for e in values)

    def _serialize_float_value(self, value) -> Union[float, str]:
        if isnan(value):
            return NAN_VALUE
        elif isinf(value):
            if value > 0:
                return POSITIVE_INFINITE_VALUE
            else:
                return NEGATIVE_INFINITE_VALUE

        # Formatting in the same way that Java does it, with a capital 'E' and without a '+' if the exponent is positive
        return str(value).upper().replace("E+", "E")
