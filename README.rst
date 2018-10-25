cassis
======

.. image:: https://travis-ci.org/dkpro/dkpro-cassis.svg?branch=master
    :target: https://travis-ci.org/dkpro/dkpro-cassis

.. image:: https://readthedocs.org/projects/cassis/badge/?version=latest
:target: https://cassis.readthedocs.io/en/latest/?badge=latest
:alt: Documentation Status
    
.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/ambv/black

**cassis** (pronunciation: [ka.sis]) is a UIMA CAS utility library in
Python. Currently supported features are:

-  Deserializing/serializing UIMA CAS from/to XMI
-  Deserializing/serializing type systems from/to XML
-  Selecting annotations, selecting covered annotations, adding
   annotations
-  Type inheritance

Some features are still under development, e.g.

-  feature encoding as XML elements (right now only XML attributes work)
-  proper type checking
-  XML/XMI schema validation
-  type unmarshalling from string to the actual type specified in the
   type system
-  reference, array and list features
-  complete sofa support

Installation
------------

To install the package from the master branch using **pip**, just run

::

    pip install git+https://github.com/dkpro/dkpro-cassis

Usage
-----

Example CAS XMI and types system files can be found under ``tests\test_files``.

Loading a CAS
~~~~~~~~~~~~~

A CAS can be deserialized from XMI either by reading from a file or
string using ``load_cas_from_xmi``.

.. code:: python

    from cassis import *

    with open('typesystem.xml', 'rb') as f:
        typesystem = load_typesystem(f)
        
    with open('cas.xml', 'rb') as f:
       cas = load_cas_from_xmi(f, typesystem=typesystem)

Adding annotations
~~~~~~~~~~~~~~~~~~

Given a type system with a type ``cassis.Token`` that has an ``id`` and
``pos`` feature, annotations can be added in the following:

.. code:: python

    from cassis import *

    with open('typesystem.xml', 'rb') as f:
        typesystem = load_typesystem(f)
        
    with open('cas.xml', 'rb') as f:
        cas = load_cas_from_xmi(f, typesystem=typesystem)
       
    Token = typesystem.get_type('cassis.Token')

    tokens = [
        Token(begin=0, end=3, id='0', pos='NNP'),
        Token(begin=4, end=10, id='1', pos='VBD'),
        Token(begin=11, end=14, id='2', pos='IN'),
        Token(begin=15, end=18, id='3', pos='DT'),
        Token(begin=19, end=24, id='4', pos='NN'),
        Token(begin=25, end=26, id='5', pos='.'),
    ]

    for token in tokens:
        cas.add_annotation(token)

Selecting annotations
~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    from cassis import *

    with open('typesystem.xml', 'rb') as f:
        typesystem = load_typesystem(f)
        
    with open('cas.xml', 'rb') as f:
        cas = load_cas_from_xmi(f, typesystem=typesystem)

    for sentence in cas.select('cassis.Sentence'):
        for token in cas.select_covered('cassis.Token', sentence):
            print(cas.get_covered_text(token))
            
            # Annotation values can be accessed as properties
            print('Token: begin={0}, end={1}, id={2}, pos={3}'.format(token.begin, token.end, token.id, token.pos)) 

Creating types and adding features
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    from cassis import *

    typesystem = TypeSystem()

    parent_type = typesystem.create_type(name='example.ParentType')
    typesystem.add_feature(type_=parent_type, name='parentFeature', rangeTypeName='String')

    child_type = typesystem.create_type(name='example.ChildType', supertypeName=parent_type.name)
    typesystem.add_feature(type_=child_type, name='childFeature', rangeTypeName='Integer')

    annotation = child_type(parentFeature='parent', childFeature='child')

When adding new features, these changes are propagated. For example,
adding a feature to a parent type makes it available to a child type.
Therefore, the type system does not need to be frozen for consistency.

Development
-----------

The required dependencies are managed by **pip**. A virtual environment
containing all needed packages for development and production can be
created and activated by

::

    virtualenv venv --python=python3 --no-site-packages
    sourve venv/bin/activate
    pip install -r requirements.txt
    pip install -r requirements_dev.txt

The tests can be run in the current environment by invoking

::

    make test

or in a clean environment via

::

    tox

.. |Build Status| image:: https://travis-ci.org/dkpro/dkpro-cassis.svg?branch=master
   :target: https://travis-ci.org/dkpro/dkpro-cassis
.. |Code style: black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/ambv/black
