"""UIMA CAS processing library in Python."""

from cassis.cas import Cas, Sofa, View
from cassis.typesystem import TypeSystem, load_typesystem
from cassis.xmi import load_cas_from_xmi

__version__ = "0.0.1"

__all__ = ["Cas", "Sofa", "View", "TypeSystem", "load_typesystem", "load_cas_from_xmi"]

del cas
del typesystem
del xmi
