import os

import pytest

from cassis import *

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "test_files")

# Small xmi


@pytest.fixture
def small_xmi_path():
    return os.path.join(FIXTURE_DIR, "xmi", "small_cas.xmi")


@pytest.fixture
def small_xmi(small_xmi_path):
    with open(small_xmi_path, "r") as f:
        return f.read()


# CAS with inheritance


@pytest.fixture
def cas_with_inheritance_xmi_path():
    return os.path.join(FIXTURE_DIR, "xmi", "cas_with_inheritance.xmi")


@pytest.fixture
def cas_with_inheritance_xmi(cas_with_inheritance_xmi_path):
    with open(cas_with_inheritance_xmi_path, "r") as f:
        return f.read()


# CAS with string arrays


@pytest.fixture
def cas_with_string_array_path():
    return os.path.join(FIXTURE_DIR, "xmi", "cas_with_string_array.xmi")


@pytest.fixture
def cas_with_string_array_xmi(cas_with_string_array_path):
    with open(cas_with_string_array_path, "r") as f:
        return f.read()


# CAS with references


@pytest.fixture
def cas_with_references_path():
    return os.path.join(FIXTURE_DIR, "xmi", "cas_with_references.xmi")


@pytest.fixture
def cas_with_references_xmi(cas_with_references_path):
    with open(cas_with_references_path, "r") as f:
        return f.read()


# CAS with non-indexed FS


@pytest.fixture
def cas_with_nonindexed_fs_path():
    return os.path.join(FIXTURE_DIR, "xmi", "cas_with_nonindexed_fs.xmi")


@pytest.fixture
def cas_with_nonindexed_fs_xmi(cas_with_nonindexed_fs_path):
    with open(cas_with_nonindexed_fs_path, "r") as f:
        return f.read()


# CAS with empty array references


@pytest.fixture
def cas_with_empty_array_references_path():
    return os.path.join(FIXTURE_DIR, "xmi", "cas_with_empty_array_reference.xmi")


@pytest.fixture
def cas_with_empty_array_references_xmi(cas_with_empty_array_references_path):
    with open(cas_with_empty_array_references_path, "r") as f:
        return f.read()


# Small type system


@pytest.fixture
def small_typesystem_path():
    return os.path.join(FIXTURE_DIR, "typesystems", "small_typesystem.xml")


@pytest.fixture
def small_typesystem_xml(small_typesystem_path):
    with open(small_typesystem_path, "r") as f:
        return f.read()


# Small type system with document annotation


@pytest.fixture
def small_typesystem_with_predefined_types_path():
    return os.path.join(FIXTURE_DIR, "typesystems", "small_typesystem_with_predefined_types.xml")


@pytest.fixture
def small_typesystem_with_predefined_types_xml(small_typesystem_with_predefined_types_path):
    with open(small_typesystem_with_predefined_types_path, "r") as f:
        return f.read()


# Type system with types without namespace
# https://github.com/dkpro/dkpro-cassis/issues/43


@pytest.fixture
def typesystem_has_types_with_no_namespace_path():
    return os.path.join(FIXTURE_DIR, "typesystems", "typesystem_has_types_with_no_namespace.xml")


@pytest.fixture
def typesystem_has_types_with_no_namespace_xml(typesystem_has_types_with_no_namespace_path):
    with open(typesystem_has_types_with_no_namespace_path, "r") as f:
        return f.read()


# Type system with inheritance


@pytest.fixture
def typesystem_with_inheritance_path():
    return os.path.join(FIXTURE_DIR, "typesystems", "typesystem_with_inheritance.xml")


@pytest.fixture
def typesystem_with_inheritance_xml(typesystem_with_inheritance_path):
    with open(typesystem_with_inheritance_path, "r") as f:
        return f.read()


# Type system with redefined DocumentAnnotation


@pytest.fixture
def typesystem_with_redefined_documentannotation_path():
    return os.path.join(FIXTURE_DIR, "typesystems", "typesystem_with_redefined_documentannotation.xml")


@pytest.fixture
def typesystem_with_redefined_documentannotation_xml(typesystem_with_redefined_documentannotation_path):
    with open(typesystem_with_redefined_documentannotation_path, "r") as f:
        return f.read()


# DKPro types


@pytest.fixture
def dkpro_typesystem_path():
    return os.path.join(FIXTURE_DIR, "typesystems", "important_dkpro_types.xml")


@pytest.fixture
def dkpro_typesystem_xml(dkpro_typesystem_path):
    with open(dkpro_typesystem_path, "r") as f:
        return f.read()


# Webanno types


@pytest.fixture
def webanno_typesystem_path():
    return os.path.join(FIXTURE_DIR, "typesystems", "webanno_types.xml")


@pytest.fixture
def webanno_typesystem_xml(webanno_typesystem_path):
    with open(webanno_typesystem_path, "r") as f:
        return f.read()


# INCEpTION types


@pytest.fixture
def inception_typesystem_path():
    return os.path.join(FIXTURE_DIR, "typesystems", "inception_typesystem.xml")


@pytest.fixture
def inception_typesystem_xml(inception_typesystem_path):
    with open(inception_typesystem_path, "r") as f:
        return f.read()


# Annotations


@pytest.fixture
def tokens(small_typesystem_xml):
    typesystem = load_typesystem(small_typesystem_xml)

    cas = Cas(typesystem)
    cas.sofa_string = "Joe waited for the train . The train was late ."

    TokenType = typesystem.get_type("cassis.Token")
    tokens = [
        TokenType(begin=0, end=3, id="0", pos="NNP"),
        TokenType(begin=4, end=10, id="1", pos="VBD"),
        TokenType(begin=11, end=14, id="2", pos="IN"),
        TokenType(begin=15, end=18, id="3", pos="DT"),
        TokenType(begin=19, end=24, id="4", pos="NN"),
        TokenType(begin=25, end=26, id="5", pos="."),
        TokenType(begin=27, end=30, id="6", pos="DT"),
        TokenType(begin=31, end=36, id="7", pos="NN"),
        TokenType(begin=37, end=40, id="8", pos="VBD"),
        TokenType(begin=41, end=45, id="9", pos="JJ"),
        TokenType(begin=46, end=47, id="10", pos="."),
    ]

    for token in tokens:
        cas.add_annotation(token)

    return tokens


@pytest.fixture
def sentences(small_typesystem_xml):
    typesystem = load_typesystem(small_typesystem_xml)
    SentenceType = typesystem.get_type("cassis.Sentence")

    cas = Cas(typesystem)
    cas.sofa_string = "Joe waited for the train . The train was late ."

    sentences = [SentenceType(begin=0, end=26, id="0"), SentenceType(begin=27, end=47, id="1")]

    for sentence in sentences:
        cas.add_annotation(sentence)

    return sentences
