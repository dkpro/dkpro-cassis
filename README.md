# cassis

**cassis** (pronunciation: [ka.sis]) is a UIMA CAS utility library in Python. Currently suported features are:

- Deserializing/serializing UIMA CAS from/to XMI
- Deserializing/serializing type systems from/to XML
- Selecting annotations, selecting covered annotations, adding annotations

Some featzers are still under development, e.g.

- feature encoding as XML elements (right now only XML attributes work)
- proper type checking
- XML/XMI schema validation
- type unmarshalling
- reference, array and list features
- complete sofa support

## Installation

tbd

## Usage

### Loading a CAS

A CAS can be deserialized from XMI either by reading from a file with `load_from_file` or from a string with `load_from_string`.

```
import cassis.cas.xmi as xmi
import cassis.typesystem as ts

typesystem = ts.load_from_file(path_to_typeystem)
cas = xmi.load_from_file(small_xmi, typesystem=typesystem)
```
    
### Adding annotations

Given a type system with a type `cassis.Token` that has an `id` and `pos` feature, annotations can be added in the following:

```
TokenType = typesystem.get_type('cassis.Token')

tokens = [
    TokenType(xmiID=13, sofa=1, begin=0, end=3, id='0', pos='NNP'),
    TokenType(xmiID=19, sofa=1, begin=4, end=10, id='1', pos='VBD'),
    TokenType(xmiID=25, sofa=1, begin=11, end=14, id='2', pos='IN'),
    TokenType(xmiID=31, sofa=1, begin=15, end=18, id='3', pos='DT'),
    TokenType(xmiID=37, sofa=1, begin=19, end=24, id='4', pos='NN'),
    TokenType(xmiID=43, sofa=1, begin=25, end=26, id='5', pos='.'),
]

for token in tokens:
    cas.add_annotation(token)
```
        
### Selecting annotations

```
for sentence in cas.select('cassis.Sentence'):
    for token in cas.select_covered('cassis.Token', sentence):
        print(cas.get_covered_text(token))
```
        
## Development

tbd
