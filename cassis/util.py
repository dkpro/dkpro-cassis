import csv
import math
import re
import struct
from collections import defaultdict
from functools import cmp_to_key
from io import IOBase, StringIO
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

from cassis import Cas
from cassis.typesystem import (
    FEATURE_BASE_NAME_BEGIN,
    FEATURE_BASE_NAME_END,
    FEATURE_BASE_NAME_HEAD,
    FEATURE_BASE_NAME_SOFA,
    FEATURE_BASE_NAME_TAIL,
    TYPE_NAME_ANNOTATION,
    TYPE_NAME_BOOLEAN_ARRAY,
    TYPE_NAME_BYTE_ARRAY,
    TYPE_NAME_DOUBLE_ARRAY,
    TYPE_NAME_FLOAT_ARRAY,
    TYPE_NAME_FS_ARRAY,
    TYPE_NAME_INTEGER_ARRAY,
    TYPE_NAME_LONG_ARRAY,
    TYPE_NAME_SHORT_ARRAY,
    TYPE_NAME_STRING_ARRAY,
    FeatureStructure,
    Type,
    is_annotation,
    is_array,
    is_list,
)

_EXCLUDED_FEATURES = {FEATURE_BASE_NAME_SOFA, FEATURE_BASE_NAME_BEGIN, FEATURE_BASE_NAME_END}
_NULL_VALUE = "<NULL>"
_ESCAPE_TRANSLATION = str.maketrans(
    {
        "\t": "\\t",
        "\n": "\\n",
        "\r": "\\r",
        "[": "\\[",
        "]": "\\]",
        ",": "\\,",
        "\\": "\\\\",
    }
)


def cas_to_comparable_text(
    cas: Cas,
    out: Optional[IOBase] = None,
    seeds: Optional[Iterable[FeatureStructure]] = None,
    mark_indexed: bool = True,
    covered_text: bool = True,
    exclude_types: Optional[Iterable[str]] = None,
) -> Optional[str]:
    return _cas_to_comparable_text(
        cas=cas,
        out=out,
        seeds=seeds,
        mark_indexed=mark_indexed,
        covered_text=covered_text,
        exclude_types=exclude_types,
    )


def _cas_to_comparable_text(
    cas: Cas,
    out: Optional[IOBase] = None,
    seeds: Optional[Iterable[FeatureStructure]] = None,
    mark_indexed: bool = True,
    covered_text: bool = True,
    exclude_types: Optional[Iterable[str]] = None,
    mark_view: bool = True,
    indexed_column: bool = False,
    treat_empty_strings_as_null: bool = False,
    max_length_covered_text: int = 30,
    sort_annotations_in_multi_valued_features: bool = True,
    unique_anchors: bool = True,
    exclude_feature_patterns: Optional[Iterable[str]] = None,
    exclude_type_patterns: Optional[Iterable[str]] = None,
    null_value: str = _NULL_VALUE,
    anchor_column: bool = True,
    type_section_header: bool = True,
    anchor_feature_hash: bool = False,
) -> Optional[str]:
    indexed_feature_structures = _get_indexed_feature_structures(cas)
    indexed_feature_structure_ids = {id(fs) for fs in indexed_feature_structures}
    all_feature_structures_by_type = _group_feature_structures_by_type(cas._find_all_fs(seeds=seeds))
    exact_excluded_types = set(exclude_types or [])
    pattern_excluded_types = list(exclude_type_patterns or [])
    pattern_excluded_features = list(exclude_feature_patterns or [])
    types_sorted = sorted(
        type_name
        for type_name in all_feature_structures_by_type.keys()
        if type_name not in exact_excluded_types and not _matches_any_pattern(type_name, pattern_excluded_types)
    )
    fs_id_to_anchor = _generate_anchors(
        cas,
        types_sorted,
        all_feature_structures_by_type,
        indexed_feature_structure_ids,
        unique_anchors=unique_anchors,
        mark_indexed=mark_indexed,
        mark_view=mark_view,
        treat_empty_strings_as_null=treat_empty_strings_as_null,
        null_value=null_value,
        exclude_feature_patterns=pattern_excluded_features,
        anchor_feature_hash=anchor_feature_hash,
    )

    string_io: Optional[StringIO] = None
    if not out:
        string_io = StringIO()
        out = string_io

    csv_writer = csv.writer(out, dialect=csv.unix_dialect)
    for t in types_sorted:
        type_ = cas.typesystem.get_type(t)

        if type_section_header:
            csv_writer.writerow([type_.name])

        is_annotation_type = covered_text and cas.typesystem.subsumes(parent=TYPE_NAME_ANNOTATION, child=type_)
        csv_writer.writerow(
            _render_header(
                type_,
                covered_text=is_annotation_type,
                indexed_column=indexed_column,
                exclude_feature_patterns=pattern_excluded_features,
                anchor_column=anchor_column,
            )
        )

        feature_structures_of_type = all_feature_structures_by_type.get(type_.name, [])

        if not feature_structures_of_type:
            continue

        rows: List[Tuple[FeatureStructure, List[str]]] = []
        for fs in feature_structures_of_type:
            row_data = _render_feature_structure(
                type_,
                fs,
                fs_id_to_anchor,
                indexed_feature_structure_ids=indexed_feature_structure_ids,
                indexed_column=indexed_column,
                max_covered_text=max_length_covered_text if is_annotation_type else 0,
                sort_annotations_in_multi_valued_features=sort_annotations_in_multi_valued_features,
                exclude_feature_patterns=pattern_excluded_features,
                treat_empty_strings_as_null=treat_empty_strings_as_null,
                null_value=null_value,
                anchor_column=anchor_column,
            )
            rows.append((fs, row_data))

        rows.sort(key=cmp_to_key(lambda a, b: _compare_rendered_rows(type_, a, b, anchor_column=anchor_column)))

        for _, row_data in rows:
            csv_writer.writerow(row_data)

    return string_io.getvalue() or None if string_io is not None else None


def _render_header(
    type_: Type,
    covered_text: bool = True,
    indexed_column: bool = False,
    exclude_feature_patterns: Optional[Iterable[str]] = None,
    anchor_column: bool = True,
) -> List[str]:
    header = []

    if anchor_column:
        header.append("<ANCHOR>")

    if indexed_column:
        header.append("<INDEXED>")

    if covered_text:
        header.append("<COVERED_TEXT>")

    for feature in _list_features(type_, exclude_feature_patterns=exclude_feature_patterns):
        header.append(feature.name)
    return header


def _render_feature_structure(
    type_: Type,
    fs: FeatureStructure,
    fs_id_to_anchor: Dict[int, str],
    indexed_feature_structure_ids: Set[int],
    indexed_column: bool = False,
    max_covered_text: int = 30,
    sort_annotations_in_multi_valued_features: bool = True,
    exclude_feature_patterns: Optional[Iterable[str]] = None,
    treat_empty_strings_as_null: bool = False,
    null_value: str = _NULL_VALUE,
    anchor_column: bool = True,
) -> List[str]:
    row_data = []

    if anchor_column:
        row_data.append(fs_id_to_anchor.get(fs.xmiID))

    if indexed_column:
        row_data.append(_bool_to_java_string(id(fs) in indexed_feature_structure_ids))

    if max_covered_text > 0 and is_annotation(fs):
        covered_text_value = _abbreviate_middle(fs.get_covered_text(), "...", max_covered_text)
        row_data.append(_escape(_render_string_value(covered_text_value, treat_empty_strings_as_null, null_value)))

    if _is_multi_valued_feature_structure(fs):
        row_data.append(
            _render_multi_valued_feature_structure(
                fs,
                fs_id_to_anchor,
                sort_annotations_in_multi_valued_features=sort_annotations_in_multi_valued_features,
                treat_empty_strings_as_null=treat_empty_strings_as_null,
                null_value=null_value,
            )
        )
        return row_data

    for feature in _list_features(type_, exclude_feature_patterns=exclude_feature_patterns):
        feature_value = fs[feature.name]
        row_data.append(
            _render_feature_value(
                feature_value,
                fs_id_to_anchor,
                sort_annotations_in_multi_valued_features=sort_annotations_in_multi_valued_features,
                treat_empty_strings_as_null=treat_empty_strings_as_null,
                null_value=null_value,
            )
        )

    return row_data


def _render_feature_value(
    feature_value: Any,
    fs_id_to_anchor: Dict[int, str],
    sort_annotations_in_multi_valued_features: bool = True,
    treat_empty_strings_as_null: bool = False,
    null_value: str = _NULL_VALUE,
) -> str:
    if feature_value is None:
        return null_value

    if isinstance(feature_value, list):
        return _render_sequence(
            feature_value,
            fs_id_to_anchor,
            sort_annotations_in_multi_valued_features=sort_annotations_in_multi_valued_features,
            treat_empty_strings_as_null=treat_empty_strings_as_null,
            null_value=null_value,
        )

    if isinstance(feature_value, FeatureStructure) and _is_multi_valued_feature_structure(feature_value):
        return _render_multi_valued_feature_structure(
            feature_value,
            fs_id_to_anchor,
            sort_annotations_in_multi_valued_features=sort_annotations_in_multi_valued_features,
            treat_empty_strings_as_null=treat_empty_strings_as_null,
            null_value=null_value,
        )

    if _is_primitive_value(feature_value):
        return _render_primitive_value(feature_value, treat_empty_strings_as_null, null_value)

    if feature_value.xmiID == 0:  # NULL FS — equivalent to Java null reference
        return null_value

    anchor = fs_id_to_anchor.get(feature_value.xmiID)
    if anchor is None:
        raise ValueError(f"No anchor for feature structure [{feature_value}] - this is a bug")
    return anchor


def _get_indexed_feature_structures(cas: Cas) -> Iterable[FeatureStructure]:
    feature_structures = []
    for sofa in cas.sofas:
        view = cas.get_view(sofa.sofaID)
        feature_structures.extend(view.select_all_fs())
    return feature_structures


def _group_feature_structures_by_type(
    feature_structures: Iterable[FeatureStructure],
) -> Dict[str, Iterable[FeatureStructure]]:
    fs_by_type = {}
    for fs in feature_structures:
        by_type_list = fs_by_type.get(fs.type.name)
        if not by_type_list:
            by_type_list = fs_by_type[fs.type.name] = []
        by_type_list.append(fs)
    return fs_by_type


def _generate_anchors(
    cas: Cas,
    types_sorted: Iterable[str],
    all_feature_structures_by_type: Dict[str, Iterable[FeatureStructure]],
    indexed_feature_structure_ids: Set[int],
    unique_anchors: bool = True,
    mark_indexed: bool = True,
    mark_view: bool = True,
    treat_empty_strings_as_null: bool = False,
    null_value: str = _NULL_VALUE,
    exclude_feature_patterns: Optional[Iterable[str]] = None,
    anchor_feature_hash: bool = False,
) -> Dict[int, str]:
    fs_id_to_anchor = {}
    disambiguation_by_prefix = defaultdict(lambda: 0)
    pattern_excluded_features = list(exclude_feature_patterns or [])
    for t in types_sorted:
        type_ = cas.typesystem.get_type(t)
        feature_structures = list(all_feature_structures_by_type[type_.name])
        feature_structures.sort(
            key=cmp_to_key(lambda a, b: _compare_fs(type_, a, b, treat_empty_strings_as_null, null_value))
        )
        include_offsets = _include_offsets(type_.name, pattern_excluded_features)

        for fs in feature_structures:
            add_index_mark = mark_indexed and id(fs) in indexed_feature_structure_ids
            anchor = _generate_anchor(
                fs,
                add_index_mark,
                mark_view=mark_view,
                include_offsets=include_offsets,
            )
            disambiguation_id = disambiguation_by_prefix.get(anchor)
            disambiguation_by_prefix[anchor] += 1
            if unique_anchors and disambiguation_id:
                anchor += f"({disambiguation_id})"
            if anchor_feature_hash:
                anchor += f"[{_feature_structure_hash(type_, fs, treat_empty_strings_as_null=treat_empty_strings_as_null, null_value=null_value) & 0xFFFFFFFF:08x}]"
            fs_id_to_anchor[fs.xmiID] = anchor
    return fs_id_to_anchor


def _include_offsets(type_name: str, exclude_feature_patterns: List[str]) -> bool:
    """Mirrors CasToComparableText_new.java includeOffsets(): offsets are omitted from the anchor
    when both begin and end for the given type are in the exclude patterns."""
    begin_excluded = f"{type_name}:{FEATURE_BASE_NAME_BEGIN}" in exclude_feature_patterns
    end_excluded = f"{type_name}:{FEATURE_BASE_NAME_END}" in exclude_feature_patterns
    return not (begin_excluded and end_excluded)


def _generate_anchor(
    fs: FeatureStructure,
    add_index_mark: bool,
    mark_view: bool = True,
    include_offsets: bool = True,
) -> str:
    anchor = fs.type.name.rsplit(".", 2)[-1]  # Get the short type name (no package)

    if include_offsets and is_annotation(fs):
        anchor += f"[{fs.begin}-{fs.end}]"

    if add_index_mark:
        anchor += "*"

    if mark_view and hasattr(fs, FEATURE_BASE_NAME_SOFA):
        anchor += f"@{fs.sofa.sofaID}"

    return anchor


def _is_primitive_value(value: Any) -> bool:
    return isinstance(value, (int, float, bool, str))


def _is_array_fs(fs: Any) -> bool:
    if not isinstance(fs, FeatureStructure):
        return False

    return is_array(fs.type)


def _is_multi_valued_feature_structure(fs: Any) -> bool:
    return isinstance(fs, FeatureStructure) and (is_array(fs.type) or is_list(fs.type))


def _compare_fs(
    type_: Type,
    a: FeatureStructure,
    b: FeatureStructure,
    treat_empty_strings_as_null: bool = False,
    null_value: str = _NULL_VALUE,
) -> int:
    if a is b:
        return 0

    # duck-typing check if something is an annotation - if yes, try sorting by offsets
    fs_a_is_annotation = is_annotation(a)
    fs_b_is_annotation = is_annotation(b)
    if fs_a_is_annotation != fs_b_is_annotation:
        return -1 if fs_a_is_annotation else 1
    if fs_a_is_annotation and fs_b_is_annotation:
        begin_cmp = a.begin - b.begin
        if begin_cmp != 0:
            return begin_cmp

        begin_cmp = b.end - a.end
        if begin_cmp != 0:
            return begin_cmp

    # Alternative implementation
    # Doing arithmetics on the hash value as we have done with the offsets does not work because the hashes do not
    # provide a global order. Hence, we map all results to 0, -1 and 1 here.
    fs_hash_a = _feature_structure_hash(
        type_, a, treat_empty_strings_as_null=treat_empty_strings_as_null, null_value=null_value
    )
    fs_hash_b = _feature_structure_hash(
        type_, b, treat_empty_strings_as_null=treat_empty_strings_as_null, null_value=null_value
    )
    if fs_hash_a == fs_hash_b:
        return 0
    return -1 if fs_hash_a < fs_hash_b else 1


def _feature_structure_hash(
    type_: Type,
    fs: FeatureStructure,
    treat_empty_strings_as_null: bool = False,
    null_value: str = _NULL_VALUE,
) -> int:
    hash_ = 0
    if _is_array_fs(fs):
        # Hash the array contents directly. Java's featureHash() iterates over named features,
        # which array types don't have, so Java effectively always returns 0 here. Using
        # content-based hashing is strictly better and avoids non-deterministic ordering when
        # multiple same-type arrays are present.
        return _compute_array_content_hash(fs.type.name, fs.elements or [], 0, treat_empty_strings_as_null, null_value)

    for feature in type_.all_features:
        if feature.name == FEATURE_BASE_NAME_SOFA:
            continue

        feature_value = getattr(fs, feature.name)

        if _is_primitive_value(feature_value):
            hash_ += _java_string_hash(
                _render_string_value(_primitive_to_java_string(feature_value), treat_empty_strings_as_null, null_value)
            )
            continue

        if _is_array_fs(feature_value):
            hash_ = _compute_array_content_hash(
                feature.rangeType.name, feature_value.elements or [], hash_, treat_empty_strings_as_null, null_value
            )
            continue

        hash_ *= -1 if feature_value is None else 1
    return hash_


def _compute_array_content_hash(
    type_name: str,
    elements: List[Any],
    hash_: int,
    treat_empty_strings_as_null: bool,
    null_value: str,
) -> int:
    # Mirrors CasToComparableText_new.java featureHash() array handling.
    # String arrays use a running-hash accumulation; all other primitive arrays use Arrays.hashCode().
    if type_name == TYPE_NAME_STRING_ARRAY:
        for element in elements:
            v = _render_string_value(element, treat_empty_strings_as_null, null_value)
            hash_ = _to_java_int(_to_java_int(31 * hash_) + hash_ + _java_string_hash(v))
        return hash_

    if type_name == TYPE_NAME_BOOLEAN_ARRAY:
        return _to_java_int(hash_ + _java_arrays_hash(elements, lambda e: 1231 if e else 1237))

    if type_name in {TYPE_NAME_BYTE_ARRAY, TYPE_NAME_INTEGER_ARRAY, TYPE_NAME_SHORT_ARRAY}:
        return _to_java_int(hash_ + _java_arrays_hash(elements, lambda e: _to_java_int(int(e))))

    if type_name == TYPE_NAME_LONG_ARRAY:
        return _to_java_int(hash_ + _java_arrays_hash(elements, lambda e: _java_long_hash(int(e))))

    if type_name == TYPE_NAME_FLOAT_ARRAY:
        return _to_java_int(hash_ + _java_arrays_hash(elements, lambda e: _java_float_hash(float(e))))

    if type_name == TYPE_NAME_DOUBLE_ARRAY:
        return _to_java_int(hash_ + _java_arrays_hash(elements, lambda e: _java_double_hash(float(e))))

    if type_name == TYPE_NAME_FS_ARRAY:
        # Integer.hashCode(x) == x in Java
        return _to_java_int(hash_ + len(elements))

    return hash_


def _matches_any_pattern(value: str, patterns: Iterable[str]) -> bool:
    return any(re.fullmatch(pattern, value) for pattern in patterns)


def _list_features(type_: Type, exclude_feature_patterns: Optional[Iterable[str]] = None) -> List[Any]:
    features = sorted(type_.all_features, key=lambda feature: feature.name)
    return [
        feature
        for feature in features
        if feature.name not in _EXCLUDED_FEATURES
        and not _matches_any_pattern(feature.name, exclude_feature_patterns or [])
    ]


def _compare_rendered_rows(
    type_: Type,
    a: Tuple[FeatureStructure, List[str]],
    b: Tuple[FeatureStructure, List[str]],
    anchor_column: bool = True,
) -> int:
    fs_cmp = _compare_fs(type_, a[0], b[0])
    if fs_cmp != 0:
        return fs_cmp

    # Skip the anchor column (index 0) when comparing row data, matching Java's .skip(1).
    # The anchor may carry disambiguation info that differs for identical FSes.
    skip = 1 if anchor_column else 0
    row_a = "\0".join(a[1][skip:])
    row_b = "\0".join(b[1][skip:])
    if row_a < row_b:
        return -1
    if row_a > row_b:
        return 1
    return 0


def _escape(value: str) -> str:
    return value.translate(_ESCAPE_TRANSLATION)


def _abbreviate_middle(value: Optional[str], middle: str, max_length: int) -> Optional[str]:
    if value is None:
        return None
    if len(value) <= max_length:
        return value

    if max_length < len(middle) + 2:
        return value

    target_length = max_length - len(middle)
    start_offset = target_length // 2 + target_length % 2
    end_offset = len(value) - target_length // 2
    return f"{value[:start_offset]}{middle}{value[end_offset:]}"


def _render_string_value(value: Optional[str], treat_empty_strings_as_null: bool, null_value: str) -> str:
    if value is None or (treat_empty_strings_as_null and value == ""):
        return null_value
    return value


def _primitive_to_java_string(value: Any) -> str:
    if isinstance(value, bool):
        return _bool_to_java_string(value)
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
    return str(value)


def _render_primitive_value(value: Any, treat_empty_strings_as_null: bool, null_value: str) -> str:
    if isinstance(value, str):
        return _escape(_render_string_value(value, treat_empty_strings_as_null, null_value))
    return _escape(_primitive_to_java_string(value))


def _render_multi_valued_feature_structure(
    fs: FeatureStructure,
    fs_id_to_anchor: Dict[int, str],
    sort_annotations_in_multi_valued_features: bool = True,
    treat_empty_strings_as_null: bool = False,
    null_value: str = _NULL_VALUE,
) -> str:
    values = _multi_valued_feature_structure_to_list(fs)

    if values is None:
        return null_value

    if sort_annotations_in_multi_valued_features and all(is_annotation(value) for value in values):
        values = sorted(values, key=lambda value: (value.begin, -value.end, value.type.name))

    return _render_sequence(
        values,
        fs_id_to_anchor,
        sort_annotations_in_multi_valued_features=sort_annotations_in_multi_valued_features,
        treat_empty_strings_as_null=treat_empty_strings_as_null,
        null_value=null_value,
    )


def _render_sequence(
    values: Iterable[Any],
    fs_id_to_anchor: Dict[int, str],
    sort_annotations_in_multi_valued_features: bool = True,
    treat_empty_strings_as_null: bool = False,
    null_value: str = _NULL_VALUE,
) -> str:
    items = []
    for item in values:
        if item is None:
            items.append(null_value)
        elif isinstance(item, str):
            items.append(_escape(_render_string_value(item, treat_empty_strings_as_null, null_value)))
        elif isinstance(item, FeatureStructure):
            if _is_multi_valued_feature_structure(item):
                items.append(
                    _render_multi_valued_feature_structure(
                        item,
                        fs_id_to_anchor,
                        sort_annotations_in_multi_valued_features=sort_annotations_in_multi_valued_features,
                        treat_empty_strings_as_null=treat_empty_strings_as_null,
                        null_value=null_value,
                    )
                )
            else:
                if item.xmiID == 0:  # NULL FS — equivalent to Java null reference
                    items.append(null_value)
                else:
                    anchor = fs_id_to_anchor.get(item.xmiID)
                    if anchor is None:
                        raise ValueError(f"No anchor for feature structure [{item}] - this is a bug")
                    items.append(anchor)
        else:
            items.append(_escape(_primitive_to_java_string(item)))
    return f"[{','.join(items)}]"


def _multi_valued_feature_structure_to_list(fs: Optional[FeatureStructure]) -> Optional[List[Any]]:
    if fs is None:
        return None

    if _is_array_fs(fs):
        return list(fs.elements or [])

    if is_list(fs.type):
        values = []
        current = fs
        while hasattr(current, FEATURE_BASE_NAME_HEAD):
            values.append(getattr(current, FEATURE_BASE_NAME_HEAD))
            current = getattr(current, FEATURE_BASE_NAME_TAIL)
        return values

    raise ValueError(f"Unsupported multi-valued feature structure type [{fs.type.name}]")


def _java_string_hash(value: str) -> int:
    hash_ = 0
    for character in value:
        hash_ = _to_java_int(31 * hash_ + ord(character))
    return hash_


def _java_arrays_hash(elements: List[Any], element_hash_fn: Callable[[Any], int]) -> int:
    """Equivalent to Java Arrays.hashCode() for primitive arrays."""
    result = 1
    for e in elements:
        result = _to_java_int(31 * result + element_hash_fn(e))
    return result


def _java_long_hash(value: int) -> int:
    unsigned_value = value & 0xFFFFFFFFFFFFFFFF
    return _to_java_int((unsigned_value ^ (unsigned_value >> 32)) & 0xFFFFFFFF)


def _java_float_hash(value: float) -> int:
    if math.isnan(value):
        bits = 0x7FC00000
    else:
        bits = struct.unpack(">I", struct.pack(">f", value))[0]
    return _to_java_int(bits)


def _java_double_hash(value: float) -> int:
    if math.isnan(value):
        bits = 0x7FF8000000000000
    else:
        bits = struct.unpack(">Q", struct.pack(">d", value))[0]
    return _to_java_int((bits ^ (bits >> 32)) & 0xFFFFFFFF)


def _to_java_int(value: int) -> int:
    value &= 0xFFFFFFFF
    if value >= 0x80000000:
        value -= 0x100000000
    return value


def _bool_to_java_string(value: bool) -> str:
    return "true" if value else "false"


def covered_by(x_begin: int, x_end: int, y_begin: int, y_end: int) -> bool:
    """Return True if span X (x_begin,x_end) is covered by span Y (y_begin,y_end).

    Equivalent to: y_begin <= x_begin and x_end <= y_end
    """
    return y_begin <= x_begin and x_end <= y_end


def covering(x_begin: int, x_end: int, y_begin: int, y_end: int) -> bool:
    """Return True if span X covers span Y.

    Equivalent to: x_begin <= y_begin and y_end <= x_end
    """
    return x_begin <= y_begin and y_end <= x_end


def colocated(x_begin: int, x_end: int, y_begin: int, y_end: int) -> bool:
    """Return True if spans X and Y have identical begin and end."""
    return x_begin == y_begin and x_end == y_end


def overlapping(x_begin: int, x_end: int, y_begin: int, y_end: int) -> bool:
    """Return True if spans X and Y overlap in any way.

    Matches the original semantics: intersection non-empty. Zero-width spans count
    as overlapping if their begin equals the other's begin or end.
    """
    return y_begin == x_begin or y_end == x_end or (x_begin < y_end and y_begin < x_end)


def overlapping_at_begin(x_begin: int, x_end: int, y_begin: int, y_end: int) -> bool:
    """Return True if X starts before Y and overlaps Y on the left."""
    return x_begin < y_begin and y_begin < x_end and x_end <= y_end


def overlapping_at_end(x_begin: int, x_end: int, y_begin: int, y_end: int) -> bool:
    """Return True if X overlaps Y on the right (starts inside Y and ends after Y)."""
    return y_begin <= x_begin and x_begin < y_end and y_end < x_end


def following(x_begin: int, x_end: int, y_begin: int, y_end: int) -> bool:
    """Return True if X starts at or after Y ends."""
    return x_begin >= y_end


def preceding(x_begin: int, x_end: int, y_begin: int, y_end: int) -> bool:
    """Return True if X ends before or at the position Y starts."""
    return y_begin >= x_end


def beginning_with(x_begin: int, x_end: int, y_begin: int, y_end: int) -> bool:
    """Return True if X and Y begin at the same position."""
    return x_begin == y_begin


def ending_with(x_begin: int, x_end: int, y_begin: int, y_end: int) -> bool:
    """Return True if X and Y end at the same position."""
    return x_end == y_end
