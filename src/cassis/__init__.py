"""UIMA CAS processing library in Python."""

from .cas import Cas, Sofa, View
from .json import load_cas_from_json
from .typesystem import (
    Annotation,
    TypeSystem,
    is_annotation,
    load_dkpro_core_typesystem,
    load_typesystem,
    merge_typesystems,
)
from .util import cas_to_comparable_text
from .xmi import load_cas_from_xmi

__all__ = [
    "Annotation",
    "Cas",
    "Sofa",
    "View",
    "TypeSystem",
    "is_annotation",
    "load_typesystem",
    "load_dkpro_core_typesystem",
    "merge_typesystems",
    "load_cas_from_xmi",
    "load_cas_from_json",
    "cas_to_comparable_text",
]
