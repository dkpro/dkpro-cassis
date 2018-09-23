import os

import pytest

import cassis.cas.xmi as xmi
import cassis.typesystem as ts

FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'test_files'
)


@pytest.fixture
def small_xmi():
    return os.path.join(FIXTURE_DIR, 'xmi', 'small_cas.xmi')


@pytest.fixture
def small_typesystem():
    return os.path.join(FIXTURE_DIR, 'typesystems', 'small_typesystem.xml')


@pytest.fixture
def tokens(small_typesystem):
    typesystem = ts.load_from_file(small_typesystem)
    TokenType = typesystem.get_type('cassis.Token')
    return [
        TokenType(xmiID=13, sofa=1, begin=0, end=3, id='0', pos='NNP'),
        TokenType(xmiID=19, sofa=1, begin=4, end=10, id='1', pos='VBD'),
        TokenType(xmiID=25, sofa=1, begin=11, end=14, id='2', pos='IN'),
        TokenType(xmiID=31, sofa=1, begin=15, end=18, id='3', pos='DT'),
        TokenType(xmiID=37, sofa=1, begin=19, end=24, id='4', pos='NN'),
        TokenType(xmiID=43, sofa=1, begin=25, end=26, id='5', pos='.'),
        TokenType(xmiID=49, sofa=1, begin=27, end=30, id='6', pos='DT'),
        TokenType(xmiID=55, sofa=1, begin=31, end=36, id='7', pos='NN'),
        TokenType(xmiID=61, sofa=1, begin=37, end=40, id='8', pos='VBD'),
        TokenType(xmiID=67, sofa=1, begin=41, end=45, id='9', pos='JJ'),
        TokenType(xmiID=73, sofa=1, begin=46, end=47, id='10', pos='.')
    ]


@pytest.fixture
def sentences(small_typesystem):
    typesystem = ts.load_from_file(small_typesystem)
    SentenceType = typesystem.get_type('cassis.Sentence')

    return [
        SentenceType(xmiID=79, sofa=1, begin=0, end=26, id='0'),
        SentenceType(xmiID=84, sofa=1, begin=27, end=47, id='1')
    ]
