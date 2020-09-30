"""UIMA CAS processing library in Python."""

from .cas import Cas, Sofa, View
from .typesystem import TypeSystem, load_dkpro_core_typesystem, load_typesystem, merge_typesystems
from .xmi import load_cas_from_xmi

__all__ = [
    "Cas",
    "Sofa",
    "View",
    "TypeSystem",
    "load_typesystem",
    "load_dkpro_core_typesystem",
    "merge_typesystems",
    "load_cas_from_xmi",
]

del cas
del typesystem
del xmi
