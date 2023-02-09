import base64
import json
import math
from collections import OrderedDict
from io import TextIOBase, TextIOWrapper
from math import isnan

from cassis.cas import NAME_DEFAULT_SOFA, Cas, IdGenerator, Sofa, View
from cassis.typesystem import *

RESERVED_FIELD_PREFIX = "%"
REF_FEATURE_PREFIX = "@"
NUMBER_FEATURE_PREFIX = "#"
ANCHOR_FEATURE_PREFIX = "^"
TYPE_FIELD = RESERVED_FIELD_PREFIX + "TYPE"
RANGE_FIELD = RESERVED_FIELD_PREFIX + "RANGE"
TYPES_FIELD = RESERVED_FIELD_PREFIX + "TYPES"
FEATURES_FIELD = RESERVED_FIELD_PREFIX + "FEATURES"
VIEWS_FIELD = RESERVED_FIELD_PREFIX + "VIEWS"
VIEW_SOFA_FIELD = RESERVED_FIELD_PREFIX + "SOFA"
VIEW_MEMBERS_FIELD = RESERVED_FIELD_PREFIX + "MEMBERS"
FEATURE_STRUCTURES_FIELD = RESERVED_FIELD_PREFIX + "FEATURE_STRUCTURES"
NAME_FIELD = RESERVED_FIELD_PREFIX + "NAME"
SUPER_TYPE_FIELD = RESERVED_FIELD_PREFIX + "SUPER_TYPE"
DESCRIPTION_FIELD = RESERVED_FIELD_PREFIX + "DESCRIPTION"
ELEMENT_TYPE_FIELD = RESERVED_FIELD_PREFIX + "ELEMENT_TYPE"
MULTIPLE_REFERENCES_ALLOWED_FIELD = RESERVED_FIELD_PREFIX + "MULTIPLE_REFERENCES_ALLOWED"
ID_FIELD = RESERVED_FIELD_PREFIX + "ID"
FLAGS_FIELD = RESERVED_FIELD_PREFIX + "FLAGS"
FLAG_DOCUMENT_ANNOTATION = "DocumentAnnotation"
ARRAY_SUFFIX = "[]"
ELEMENTS_FIELD = RESERVED_FIELD_PREFIX + "ELEMENTS"
NAN_VALUE = "NaN"
POSITIVE_INFINITE_VALUE = "Infinity"
POSITIVE_INFINITE_VALUE_ABBR = "Inf"
NEGATIVE_INFINITE_VALUE = "-Infinity"
NEGATIVE_INFINITE_VALUE_ABBR = "-Inf"


def load_cas_from_json(source: Union[IO, str], typesystem: TypeSystem = None) -> Cas:
    """Loads a CAS from a JSON source.

    Args:
        source: The JSON source. If `source` is a string, then it is assumed to be an JSON string.
            If `source` is a file-like object, then the data is read from it.
        typesystem: The type system that belongs to this CAS. If `None`, an empty type system is provided.
        lenient: If `True`, unknown Types will be ignored. If `False`, unknown Types will cause an exception.
            The default is `False`.

    Returns:
        The deserialized CAS

    """
    if typesystem is None:
        typesystem = TypeSystem()

    deserializer = CasJsonDeserializer()
    return deserializer.deserialize(source, typesystem=typesystem)


class CasJsonDeserializer:
    def __init__(self):
        self._max_xmi_id = 0
        self._max_sofa_num = 0
        self._post_processors = []

    def deserialize(self, source: Union[IO, str], typesystem: Optional[TypeSystem] = None) -> Cas:
        if isinstance(source, str):
            data = json.loads(source)
        else:
            data = json.load(source)

        self._max_xmi_id = 0
        self._max_sofa_num = 0
        self._post_processors = []

        embedded_typesystem = TypeSystem()
        json_typesystem = data.get(TYPES_FIELD)

        # First, build a dependency graph to support cases where a child type is defined before its super type
        type_dependencies = defaultdict(set)
        for type_name, json_type in json_typesystem.items():
            type_dependencies[type_name].add(json_type[SUPER_TYPE_FIELD])

        # Second, load all the types but no features since features of a type X might be of a later loaded type Y
        for type_name in toposort_flatten(type_dependencies):
            if is_predefined(type_name):
                continue

            self._parse_type(embedded_typesystem, type_name, json_typesystem[type_name])

        # Now we are sure we know all the types, we can create the features
        for type_name, json_type in json_typesystem.items():
            self._parse_features(embedded_typesystem, type_name, json_type)

        typesystem = merge_typesystems(typesystem, embedded_typesystem)

        cas = Cas(typesystem=typesystem)

        feature_structures = {}
        json_feature_structures = data.get(FEATURE_STRUCTURES_FIELD)
        if isinstance(json_feature_structures, list):
            for json_fs in json_feature_structures:
                if json_fs.get(TYPE_FIELD) == TYPE_NAME_SOFA:
                    fs_id = json_fs.get(ID_FIELD)
                    fs = self._parse_sofa(cas, fs_id, json_fs, feature_structures)
                else:
                    fs_id = json_fs.get(ID_FIELD)
                    fs = self._parse_feature_structure(typesystem, fs_id, json_fs, feature_structures)
                feature_structures[fs.xmiID] = fs

        if isinstance(json_feature_structures, dict):
            for fs_id, json_fs in json_feature_structures.items():
                if json_fs.get(TYPE_FIELD) == TYPE_NAME_SOFA:
                    fs_id = int(fs_id)
                    fs = self._parse_sofa(cas, fs_id, json_fs, feature_structures)
                else:
                    fs_id = int(fs_id)
                    fs = self._parse_feature_structure(typesystem, fs_id, json_fs, feature_structures)
                feature_structures[fs.xmiID] = fs

        for post_processor in self._post_processors:
            post_processor()

        cas._xmi_id_generator = IdGenerator(self._max_xmi_id + 1)
        cas._sofa_num_generator = IdGenerator(self._max_sofa_num + 1)

        # At this point all views for which we have a sofa with a known ID and sofaNum have already been created
        # as part of parsing the feature structures. Thus, if there are any views remaining that are only declared
        # in the views section, we just create them with auto-assigned IDs
        json_views = data.get(VIEWS_FIELD)
        for view_name, json_view in json_views.items():
            self._parse_view(cas, view_name, json_view, feature_structures)

        return cas

    def _parse_type(self, typesystem: TypeSystem, type_name: str, json_type: Dict[str, any]):
        super_type_name = json_type[SUPER_TYPE_FIELD]
        description = json_type.get(DESCRIPTION_FIELD)
        typesystem.create_type(type_name, super_type_name, description=description)

    def _parse_features(self, typesystem: TypeSystem, type_name: str, json_type: Dict[str, any]):
        new_type = typesystem.get_type(type_name)
        for key, json_feature in json_type.items():
            if key.startswith(RESERVED_FIELD_PREFIX):
                continue
            typesystem.create_feature(
                new_type,
                name=key,
                rangeType=json_feature[RANGE_FIELD],
                description=json_feature.get(DESCRIPTION_FIELD),
                elementType=json_feature.get(ELEMENT_TYPE_FIELD),
                multipleReferencesAllowed=json_feature.get(MULTIPLE_REFERENCES_ALLOWED_FIELD),
            )

    def _get_or_create_view(
        self, cas: Cas, view_name: str, fs_id: Optional[int] = None, sofa_num: Optional[int] = None
    ) -> Cas:
        if view_name == NAME_DEFAULT_SOFA:
            view = cas.get_view(NAME_DEFAULT_SOFA)

            # We need to make sure that the sofa gets the real xmi, see #155
            if fs_id is not None:
                view.get_sofa().xmiID = fs_id

            return view
        else:
            return cas.create_view(view_name, xmiID=fs_id, sofaNum=sofa_num)

    def _parse_view(self, cas: Cas, view_name: str, json_view: Dict[str, any], feature_structures: Dict[str, any]):
        view = self._get_or_create_view(cas, view_name)
        for member_id in json_view[VIEW_MEMBERS_FIELD]:
            fs = feature_structures[member_id]
            view.add(fs, keep_id=True)

    def _parse_sofa(self, cas: Cas, fs_id: int, json_fs: Dict[str, any], feature_structures: Dict[int, any]) -> Sofa:
        view = self._get_or_create_view(
            cas, json_fs.get(FEATURE_BASE_NAME_SOFAID), fs_id, json_fs.get(FEATURE_BASE_NAME_SOFANUM)
        )

        view.sofa_string = json_fs.get(FEATURE_BASE_NAME_SOFASTRING)
        view.sofa_mime = json_fs.get(FEATURE_BASE_NAME_SOFAMIME)
        view.sofa_uri = json_fs.get(FEATURE_BASE_NAME_SOFAURI)
        view.sofa_array = feature_structures.get(json_fs.get(REF_FEATURE_PREFIX + FEATURE_BASE_NAME_SOFAARRAY))

        return view.get_sofa()

    def _parse_feature_structure(
        self, typesystem: TypeSystem, fs_id: int, json_fs: Dict[str, any], feature_structures: Dict[int, any]
    ):
        AnnotationType = typesystem.get_type(json_fs.get(TYPE_FIELD))

        attributes = dict(json_fs)

        # Map the JSON FS ID to xmiID
        attributes["xmiID"] = fs_id

        # Remap features that use a reserved Python name
        if "self" in attributes:
            attributes["self_"] = attributes.pop("self")

        if "type" in attributes:
            attributes["type_"] = attributes.pop("type")

        if typesystem.is_primitive_array(AnnotationType.name):
            attributes["elements"] = self._parse_primitive_array(AnnotationType.name, json_fs.get(ELEMENTS_FIELD))
        elif AnnotationType.name == TYPE_NAME_FS_ARRAY:
            # Resolve id-ref at the end of processing
            def fix_up(elements):
                return lambda: setattr(fs, "elements", [feature_structures.get(e) for e in elements])

            self._post_processors.append(fix_up(json_fs.get(ELEMENTS_FIELD)))

        self._strip_reserved_json_keys(attributes)

        ref_features = {}
        for key, value in list(attributes.items()):
            if key.startswith(REF_FEATURE_PREFIX):
                ref_features[key[1:]] = value
                attributes.pop(key)
            if key.startswith(NUMBER_FEATURE_PREFIX):
                attributes[key[1:]] = self._parse_float_value(value)
                attributes.pop(key)

        self._max_xmi_id = max(attributes["xmiID"], self._max_xmi_id)
        fs = AnnotationType(**attributes)

        self._resolve_references(fs, ref_features, feature_structures)

        # Map from offsets in UIMA UTF-16 based offsets to Unicode codepoints
        if typesystem.is_instance_of(fs.type, TYPE_NAME_ANNOTATION):
            sofa = fs.sofa
            fs.begin = sofa._offset_converter.external_to_python(fs.begin)
            fs.end = sofa._offset_converter.external_to_python(fs.end)

        return fs

    def _parse_float_value(self, value: Union[str, float]) -> float:
        if isinstance(value, float):
            return value
        elif value == NAN_VALUE:
            return float("nan")
        elif value == POSITIVE_INFINITE_VALUE or value == POSITIVE_INFINITE_VALUE_ABBR:
            return float("inf")
        elif value == NEGATIVE_INFINITE_VALUE or value == NEGATIVE_INFINITE_VALUE_ABBR:
            return float("-inf")

        raise ValueError(
            f"Illegal floating point value [{value}]. Must be a float literal or one of {NAN_VALUE}, "
            f"{POSITIVE_INFINITE_VALUE}, {POSITIVE_INFINITE_VALUE_ABBR}, {NEGATIVE_INFINITE_VALUE}, or "
            f"{NEGATIVE_INFINITE_VALUE_ABBR}"
        )

    def _parse_primitive_array(self, type_name: str, elements: [list, str]) -> List:
        if elements and type_name == TYPE_NAME_BYTE_ARRAY:
            return base64.b64decode(elements)
        if elements and (type_name == TYPE_NAME_FLOAT_ARRAY or type_name == TYPE_NAME_DOUBLE_ARRAY):
            return [self._parse_float_value(v) for v in elements]
        else:
            return elements

    def _resolve_references(self, fs, ref_features: Dict[str, any], feature_structures: Dict[int, any]):
        for key, value in ref_features.items():
            target_fs = feature_structures.get(value)
            if target_fs:
                # Resolve id-ref now
                setattr(fs, key, target_fs)
            else:
                # Resolve id-ref at the end of processing
                def fix_up(k, v):
                    return lambda: setattr(fs, k, feature_structures.get(v))

                self._post_processors.append(fix_up(key, value))

    def _strip_reserved_json_keys(
        self,
        attributes: Dict[str, any],
    ):
        for key in list(attributes):
            if key.startswith(RESERVED_FIELD_PREFIX):
                attributes.pop(key)


class CasJsonSerializer:
    _COMMON_FIELD_NAMES = {"xmiID", "type"}

    def __init__(self):
        pass

    def serialize(
        self,
        sink: Union[IO, str, None],
        cas: Cas,
        pretty_print: bool = True,
        ensure_ascii: bool = False,
        type_system_mode: TypeSystemMode = TypeSystemMode.FULL,
    ) -> Union[str, None]:
        feature_structures = []

        views = {}
        for view in cas.views:
            views[view.sofa.sofaID] = self._serialize_view(view)

            if view.sofa.sofaArray:
                json_sofa_array_fs = self._serialize_feature_structure(view.sofa.sofaArray)
                feature_structures.append(json_sofa_array_fs)
            json_sofa_fs = self._serialize_feature_structure(view.sofa)
            feature_structures.append(json_sofa_fs)

        # Find all fs, even the ones that are not directly added to a sofa
        used_types = set()
        for fs in sorted(cas._find_all_fs(include_inlinable_arrays_and_lists=True), key=lambda a: a.xmiID):
            used_types.add(fs.type)
            json_fs = self._serialize_feature_structure(fs)
            feature_structures.append(json_fs)

        types = None
        if type_system_mode is not TypeSystemMode.NONE:
            types = {}

            if type_system_mode is TypeSystemMode.MINIMAL:
                # Build transitive closure of used types by following parents, features, etc.
                types_to_include = cas.typesystem.transitive_closure(used_types)
            elif type_system_mode is TypeSystemMode.FULL:
                types_to_include = cas.typesystem.get_types()
            else:
                raise Exception(f"Invalid type system mode: [{type_system_mode}]")

            for type_ in sorted(types_to_include, key=lambda x: x.name):
                if type_.name == TYPE_NAME_DOCUMENT_ANNOTATION:
                    continue
                json_type = self._serialize_type(type_)
                types[json_type[NAME_FIELD]] = json_type

        data = {}
        if types is not None:
            data[TYPES_FIELD] = types
        if feature_structures is not None:
            data[FEATURE_STRUCTURES_FIELD] = feature_structures
        if views is not None:
            data[VIEWS_FIELD] = views

        if sink and not isinstance(sink, TextIOBase):
            sink = TextIOWrapper(sink, encoding="utf-8", write_through=True)

        if sink:
            json.dump(
                data,
                sink,
                sort_keys=False,
                indent=2 if pretty_print else None,
                ensure_ascii=ensure_ascii,
                allow_nan=False,
            )
        else:
            return json.dumps(
                data, sort_keys=False, indent=2 if pretty_print else None, ensure_ascii=ensure_ascii, allow_nan=False
            )

        if isinstance(sink, TextIOWrapper):
            sink.detach()  # Prevent TextIOWrapper from closing the BytesIO

        return None

    def _serialize_type(self, type_: Type):
        type_name = self._to_external_type_name(type_.name)
        supertype_name = self._to_external_type_name(type_.supertype.name)

        json_type = {
            NAME_FIELD: type_name,
            SUPER_TYPE_FIELD: supertype_name,
        }

        if type_.description:
            json_type[DESCRIPTION_FIELD] = type_.description

        for feature in list(type_.features):
            json_feature = self._serialize_feature(json_type, feature)
            json_type[json_feature[NAME_FIELD]] = json_feature

        return json_type

    def _serialize_feature(self, json_type, feature: Feature):
        # If the feature name is a reserved name like `self`, then we added an
        # underscore to it before so Python can handle it. We now need to remove it.
        feature_name = feature.name
        if feature._has_reserved_name:
            feature_name = feature_name[:-1]

        json_feature = {
            NAME_FIELD: feature_name,
            RANGE_FIELD: self._to_external_type_name(feature.rangeType.name),
        }

        if feature.description:
            json_feature[DESCRIPTION_FIELD] = feature.description

        if feature.multipleReferencesAllowed is not None:
            json_feature[MULTIPLE_REFERENCES_ALLOWED_FIELD] = feature.multipleReferencesAllowed

        if feature.elementType is not None:
            json_feature[ELEMENT_TYPE_FIELD] = self._to_external_type_name(feature.elementType.name)

        return json_feature

    def _serialize_feature_structure(self, fs) -> dict:
        type_name = fs.type.name

        json_fs = OrderedDict()
        json_fs[ID_FIELD] = fs.xmiID
        json_fs[TYPE_FIELD] = type_name

        if type_name == TYPE_NAME_BYTE_ARRAY:
            if fs.elements:
                json_fs[ELEMENTS_FIELD] = base64.b64encode(bytes(fs.elements)).decode("ascii")
            return json_fs
        elif type_name in {TYPE_NAME_DOUBLE_ARRAY, TYPE_NAME_FLOAT_ARRAY}:
            if fs.elements:
                json_fs[ELEMENTS_FIELD] = [self._serialize_float_value(e) for e in fs.elements]
            return json_fs
        elif is_primitive_array(fs.type):
            if fs.elements:
                json_fs[ELEMENTS_FIELD] = fs.elements
            return json_fs
        elif TYPE_NAME_FS_ARRAY == type_name:
            if fs.elements:
                json_fs[ELEMENTS_FIELD] = [self._serialize_ref(e) for e in fs.elements]
            return json_fs

        for feature in fs.type.all_features:
            if feature.name in CasJsonSerializer._COMMON_FIELD_NAMES:
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
            if feature.domainType.name == TYPE_NAME_ANNOTATION and feature_name == "begin" or feature_name == "end":
                sofa: Sofa = getattr(fs, "sofa")
                value = sofa._offset_converter.python_to_external(value)

            if feature.rangeType.name in {TYPE_NAME_DOUBLE, TYPE_NAME_FLOAT}:
                float_value = self._serialize_float_value(value)
                if isinstance(float_value, str):
                    feature_name = NUMBER_FEATURE_PREFIX + feature_name
                json_fs[feature_name] = self._serialize_float_value(value)
            elif is_primitive(feature.rangeType):
                json_fs[feature_name] = value
            else:
                # We need to encode non-primitive features as a reference
                json_fs[REF_FEATURE_PREFIX + feature_name] = self._serialize_ref(value)
        return json_fs

    def _serialize_float_value(self, value) -> Union[float, str]:
        if isnan(value):
            return NAN_VALUE
        elif math.isinf(value):
            if value > 0:
                return POSITIVE_INFINITE_VALUE
            else:
                return NEGATIVE_INFINITE_VALUE
        return value

    def _serialize_ref(self, fs) -> int:
        if not fs:
            return None

        return fs.xmiID

    def _serialize_view(self, view: View):
        return {
            VIEW_SOFA_FIELD: view.sofa.xmiID,
            VIEW_MEMBERS_FIELD: sorted(x.xmiID for x in view.get_all_annotations()),
        }

    def _to_external_type_name(self, type_name: str):
        if type_name.startswith("uima.noNamespace."):
            return type_name.replace("uima.noNamespace.", "")
        return type_name
