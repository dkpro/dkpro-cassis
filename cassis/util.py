import csv
from collections import defaultdict
from functools import cmp_to_key
from io import IOBase, StringIO
from typing import Dict, Iterable, Set

from cassis import Cas
from cassis.typesystem import FEATURE_BASE_NAME_SOFA, TYPE_NAME_ANNOTATION, FeatureStructure, Type, is_array

_EXCLUDED_FEATURES = {FEATURE_BASE_NAME_SOFA}
_NULL_VALUE = "<NULL>"


def cas_to_comparable_text(
    cas: Cas,
    out: [IOBase, None] = None,
    seeds: Iterable[FeatureStructure] = None,
    mark_indexed: bool = True,
    covered_text: bool = True,
    exclude_types: Set[str] = None,
) -> [str, None]:
    indexed_feature_structures = _get_indexed_feature_structures(cas)
    all_feature_structures_by_type = _group_feature_structures_by_type(cas._find_all_fs(seeds=seeds))
    types_sorted = sorted(all_feature_structures_by_type.keys())
    fs_id_to_anchor = _generate_anchors(
        cas, types_sorted, all_feature_structures_by_type, indexed_feature_structures, mark_indexed=mark_indexed
    )

    if not out:
        out = StringIO()

    csv_writer = csv.writer(out, dialect=csv.unix_dialect)
    for t in types_sorted:
        if exclude_types and t in exclude_types:
            continue

        type_ = cas.typesystem.get_type(t)

        csv_writer.writerow([type_.name])

        is_annotation_type = covered_text and cas.typesystem.subsumes(parent=TYPE_NAME_ANNOTATION, child=type_)
        csv_writer.writerow(_render_header(type_, covered_text=is_annotation_type))

        feature_structures_of_type = all_feature_structures_by_type.get(type_.name)

        if not feature_structures_of_type:
            continue

        for fs in feature_structures_of_type:
            row_data = _render_feature_structure(
                type_, fs, fs_id_to_anchor, max_covered_text=30 if is_annotation_type else 0
            )
            csv_writer.writerow(row_data)

    return out.getvalue() or None


def _render_header(type_: Type, covered_text: bool = True) -> []:
    header = ["<ANCHOR>"]

    if covered_text:
        header.append("<COVERED_TEXT>")

    for feature in sorted(type_.all_features, key=lambda v: v.name):
        if feature.name in _EXCLUDED_FEATURES:
            continue

        header.append(feature.name)
    return header


def _render_feature_structure(
    type_: Type, fs: FeatureStructure, fs_id_to_anchor: Dict[int, str], max_covered_text: int = 30
) -> []:
    row_data = [fs_id_to_anchor.get(fs.xmiID)]

    if max_covered_text > 0 and _is_annotation_fs(fs):
        covered_text = fs.get_covered_text()
        if covered_text and len(covered_text) >= max_covered_text:
            prefix = covered_text[0 : (max_covered_text // 2)]
            suffix = covered_text[-(max_covered_text // 2) :]
            covered_text = f"{prefix}...{suffix}"
        row_data.append(covered_text if covered_text is not None else _NULL_VALUE)

    if _is_array_fs(fs):
        row_data.append(_render_feature_value(fs.elements, fs_id_to_anchor))
        return row_data

    for feature in sorted(type_.all_features, key=lambda v: v.name):
        if feature.name in _EXCLUDED_FEATURES:
            continue

        feature_value = fs[feature.name]
        row_data.append(_render_feature_value(feature_value, fs_id_to_anchor))

    return row_data


def _render_feature_value(feature_value: any, fs_id_to_anchor: Dict[int, str]) -> any:
    if feature_value is None:
        return _NULL_VALUE
    elif isinstance(feature_value, list):
        return [_render_feature_value(e, fs_id_to_anchor) for e in feature_value]
    elif _is_array_fs(feature_value):
        if feature_value.elements is not None:
            return [_render_feature_value(e, fs_id_to_anchor) for e in feature_value.elements]
    elif _is_primitive_value(feature_value):
        return feature_value
    else:
        return fs_id_to_anchor.get(feature_value.xmiID)


def _get_indexed_feature_structures(cas: Cas) -> Iterable[FeatureStructure]:
    feature_structures = []
    for sofa in cas.sofas:
        view = cas.get_view(sofa.sofaID)
        feature_structures.extend(view.select_all())
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
    indexed_feature_structures: Iterable[FeatureStructure],
    unique_anchors: bool = True,
    mark_indexed: bool = True,
) -> Dict[int, str]:
    fs_id_to_anchor = {}
    disambiguation_by_prefix = defaultdict(lambda: 0)
    for t in types_sorted:
        type_ = cas.typesystem.get_type(t)
        feature_structures = all_feature_structures_by_type[type_.name]
        feature_structures.sort(key=cmp_to_key(lambda a, b: _compare_fs(type_, a, b)))

        for fs in feature_structures:
            add_index_mark = mark_indexed and fs in indexed_feature_structures
            anchor = _generate_anchor(fs, add_index_mark)
            disambiguation_id = disambiguation_by_prefix.get(anchor)
            disambiguation_by_prefix[anchor] += 1
            if unique_anchors and disambiguation_id:
                anchor += f"({disambiguation_id})"
            fs_id_to_anchor[fs.xmiID] = anchor
    return fs_id_to_anchor


def _generate_anchor(fs: FeatureStructure, add_index_mark: bool) -> str:
    anchor = fs.type.name.rsplit(".", 2)[-1]  # Get the short type name (no package)

    if _is_annotation_fs(fs):
        anchor += f"[{fs.begin}-{fs.end}]"

    if add_index_mark:
        anchor += "*"

    if hasattr(fs, FEATURE_BASE_NAME_SOFA):
        anchor += f"@{fs.sofa.sofaID}"

    return anchor


def _is_primitive_value(value: any) -> bool:
    return type(value) in (int, float, bool, str)


def _is_array_fs(fs: FeatureStructure) -> bool:
    if not isinstance(fs, FeatureStructure):
        return False

    return is_array(fs.type)


def _is_annotation_fs(fs: FeatureStructure) -> bool:
    return hasattr(fs, "begin") and isinstance(fs.begin, int) and hasattr(fs, "end") and isinstance(fs.end, int)


def _compare_fs(type_: Type, a: FeatureStructure, b: FeatureStructure) -> int:
    if a is b:
        return 0

    # duck-typing check if something is a annotation - if yes, try sorting by offets
    fs_a_is_annotation = _is_annotation_fs(a)
    fs_b_is_annotation = _is_annotation_fs(b)
    if fs_a_is_annotation != fs_b_is_annotation:
        return -1
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
    fs_hash_a = _feature_structure_hash(type_, a)
    fs_hash_b = _feature_structure_hash(type_, b)
    if fs_hash_a == fs_hash_b:
        return 0
    return -1 if fs_hash_a < fs_hash_b else 1


def _feature_structure_hash(type_: Type, fs: FeatureStructure):
    hash_ = 0
    if _is_array_fs(fs):
        return len(fs.elements) if fs.elements else 0

    # Should be possible to get away with not sorting here assuming that all_features returns the features always in
    # the same order
    for feature in type_.all_features:
        if feature.name == FEATURE_BASE_NAME_SOFA:
            continue

        feature_value = getattr(fs, feature.name)

        if _is_array_fs(feature_value):
            if feature_value.elements is not None:
                for element in feature_value.elements:
                    hash_ = _feature_value_hash(feature_value, hash_)
        else:
            hash_ = _feature_value_hash(feature_value, hash_)
    return hash_


def _feature_value_hash(feature_value: any, hash_: int):
    # Note we do not recurse further into arrays here because that could lead to endless loops!
    if type(feature_value) in (int, float, bool, str):
        return hash_ + hash(feature_value)
    else:
        # If we get here, it is a feature structure reference... we cannot really recursively
        # go into it to calculate a recursive hash... so we just check if the value is non-null
        return hash_ * (-1 if feature_value is None else 1)
