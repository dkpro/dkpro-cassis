# cassis

[![Build Status](https://travis-ci.org/dkpro/dkpro-cassis.svg?branch=master)](https://travis-ci.org/dkpro/dkpro-cassis)

**cassis** (pronunciation: [ka.sis]) is a UIMA CAS utility library in Python. Currently supported features are:

- Deserializing/serializing UIMA CAS from/to XMI
- Deserializing/serializing type systems from/to XML
- Selecting annotations, selecting covered annotations, adding annotations

Some features are still under development, e.g.

- feature encoding as XML elements (right now only XML attributes work)
- proper type checking
- XML/XMI schema validation
- type unmarshalling from string to the actual type specified in the type system
- reference, array and list features
- complete sofa support

## Installation

tbd

## Usage

Example CAS XMI and types system files can be found under `tests\test_files`. 

### Loading a CAS

A CAS can be deserialized from XMI either by reading from a file or string using `load_cas_from_xmi`.

```python
from cassis import *

with open('typesystem.xml', 'rb') as f:
    typesystem = load_typesystem(f)
    
with open('cas.xml', 'rb') as f:
   cas = load_cas_from_xmi(f, typesystem=typesystem)

```
    
### Adding annotations

Given a type system with a type `cassis.Token` that has an `id` and `pos` feature, annotations can be added in the following:

```python
from cassis import *

with open('typesystem.xml', 'rb') as f:
    typesystem = load_typesystem(f)
    
with open('cas.xml', 'rb') as f:
   cas = load_cas_from_xmi(f, typesystem=typesystem)
   
Token = typesystem.get_type('cassis.Token')

tokens = [
    Token(xmiID=13, sofa=1, begin=0, end=3, id='0', pos='NNP'),
    Token(xmiID=19, sofa=1, begin=4, end=10, id='1', pos='VBD'),
    Token(xmiID=25, sofa=1, begin=11, end=14, id='2', pos='IN'),
    Token(xmiID=31, sofa=1, begin=15, end=18, id='3', pos='DT'),
    Token(xmiID=37, sofa=1, begin=19, end=24, id='4', pos='NN'),
    Token(xmiID=43, sofa=1, begin=25, end=26, id='5', pos='.'),
]

for token in tokens:
    cas.add_annotation(token)
```
        
### Selecting annotations

```python
from cassis import *

with open('typesystem.xml', 'rb') as f:
    typesystem = load_typesystem(f)
    
with open('cas.xml', 'rb') as f:
   cas = load_cas_from_xmi(f, typesystem=typesystem)

for sentence in cas.select('cassis.Sentence'):
    for token in cas.select_covered('cassis.Token', sentence):
        print(cas.get_covered_text(token))
```
        
## Development

The required dependencies are managed by [pipenv](https://docs.pipenv.org/). A virtual environment containing all needed packages for development and production can be created and activated by

    pipenv shell

. The tests can be run in the current environment by invoking

    make test
    
or in a clean environment via

    tox
