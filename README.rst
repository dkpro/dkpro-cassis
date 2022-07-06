dkpro-cassis
============

.. image:: https://travis-ci.org/dkpro/dkpro-cassis.svg?branch=master
  :target: https://travis-ci.org/dkpro/dkpro-cassis

.. image:: https://readthedocs.org/projects/cassis/badge/?version=latest
  :target: https://cassis.readthedocs.io/en/latest/?badge=latest
  :alt: Documentation Status

.. image:: https://codecov.io/gh/dkpro/dkpro-cassis/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/dkpro/dkpro-cassis

.. image:: https://img.shields.io/pypi/l/dkpro-cassis.svg
  :alt: PyPI - License
  :target: https://pypi.org/project/dkpro-cassis/

.. image:: https://img.shields.io/pypi/pyversions/dkpro-cassis.svg
  :alt: PyPI - Python Version
  :target: https://pypi.org/project/dkpro-cassis/

.. image:: https://img.shields.io/pypi/v/dkpro-cassis.svg
  :alt: PyPI
  :target: https://pypi.org/project/dkpro-cassis/

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
  :target: https://github.com/ambv/black
  
DKPro **cassis** (pronunciation: [ka.sis]) provides a pure-Python implementation of the *Common Analysis System* (CAS)
as defined by the `UIMA <https://uima.apache.org>`_ framework. The CAS is a data structure representing an object to
be enriched with annotations (the co-called *Subject of Analysis*, short *SofA*).

This library enables the creation and manipulation of CAS objects and their associated type systems as well as loading
and saving CAS objects in the `CAS XMI XML representation <https://uima.apache.org/d/uimaj-current/references.html#ugr.ref.xmi>`_
in Python programs. This can ease in particular the integration of Python-based Natural Language Processing (e.g.
`spacy <https://spacy.io>`_ or `NLTK <https://www.nltk.org>`_) and Machine Learning librarys (e.g.
`scikit-learn <https://scikit-learn.org/stable/>`_ or `Keras <https://keras.io>`_) in UIMA-based text analysis workflows.

An example of cassis in action is the `spacy recommender for INCEpTION <https://github.com/inception-project/external-recommender-spacy>`_,
which wraps the spacy NLP library as a web service which can be used in conjunction with the `INCEpTION <https://inception-project.github.io>`_
text annotation platform to automatically generate annotation suggestions.

Features
--------

Currently supported features are:

- Text SofAs
- Deserializing/serializing UIMA CAS from/to XMI
- Deserializing/serializing type systems from/to XML
- Selecting annotations, selecting covered annotations, adding
  annotations
- Type inheritance
- Multiple SofA support
- Type system can be changed after loading
- Primitive and reference features and arrays of primitives and references

Some features are still under development, e.g.

- Proper type checking
- XML/XMI schema validation
- `UIMA JSON CAS support <https://github.com/apache/uima-uimaj-io-jsoncas#readme>`_ (the format is not yet finalized)

Installation
------------

To install the package with :code:`pip`, just run

    pip install dkpro-cassis

Usage
-----

Example CAS XMI and types system files can be found under :code:`tests\test_files`.

Loading a CAS
~~~~~~~~~~~~~

A CAS can be deserialized from XMI either by reading from a file or
string using :code:`load_cas_from_xmi`.

.. code:: python

    from cassis import *

    with open('typesystem.xml', 'rb') as f:
        typesystem = load_typesystem(f)
        
    with open('cas.xmi', 'rb') as f:
       cas = load_cas_from_xmi(f, typesystem=typesystem)

Saving a CAS as XMI
~~~~~~~~~~~~~~~~~~~

A CAS can be serialized to XMI either by writing to a file or be
returned as a string using :code:`cas.to_xmi()`.

.. code:: python

    from cassis import *

    with open('cas.xmi', 'rb') as f:
       cas = load_cas_from_xmi(f)

    # Returned as a string
    xmi = cas.to_xmi()

    # Written to file
    cas.to_xmi("my_cas.xmi")

Adding annotations
~~~~~~~~~~~~~~~~~~

Given a type system with a type :code:`cassis.Token` that has an :code:`id` and
:code:`pos` feature, annotations can be added in the following:

.. code:: python

    from cassis import *

    with open('typesystem.xml', 'rb') as f:
        typesystem = load_typesystem(f)
        
    with open('cas.xmi', 'rb') as f:
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
        cas.add(token)

Selecting annotations
~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    from cassis import *

    with open('typesystem.xml', 'rb') as f:
        typesystem = load_typesystem(f)
        
    with open('cas.xmi', 'rb') as f:
        cas = load_cas_from_xmi(f, typesystem=typesystem)

    for sentence in cas.select('cassis.Sentence'):
        for token in cas.select_covered('cassis.Token', sentence):
            print(token.get_covered_text())
            
            # Annotation values can be accessed as properties
            print('Token: begin={0}, end={1}, id={2}, pos={3}'.format(token.begin, token.end, token.id, token.pos)) 

Getting and setting (nested) features
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want to access a variable but only have its name as a string or have nested feature structures,
e.g. a feature structure  with feature :code:`a` that has a
feature :code:`b` that has a feature :code:`c`, some of which can be :code:`None`, then you can use the
following:

.. code:: python

    fs.get("var_name") # Or
    fs["var_name"]

Or in the nested case,

.. code:: python

    fs.get("a.b.c")
    fs["a.b.c"]


If :code:`a` or  :code:`b` or  :code:`c` are :code:`None`, then this returns instead of
throwing an error.

Another example would be a StringList containing :code:`["Foo", "Bar", "Baz"]`:

.. code:: python

    assert lst.get("head") == "foo"
    assert lst.get("tail.head") == "bar"
    assert lst.get("tail.tail.head") == "baz"
    assert lst.get("tail.tail.tail.head") == None
    assert lst.get("tail.tail.tail.tail.head") == None

The same goes for setting:

.. code:: python

    # Functional
    lst.set("head", "new_foo")
    lst.set("tail.head", "new_bar")
    lst.set("tail.tail.head", "new_baz")

    assert lst.get("head") == "new_foo"
    assert lst.get("tail.head") == "new_bar"
    assert lst.get("tail.tail.head") == "new_baz"

    # Bracket access
    lst["head"] = "newer_foo"
    lst["tail.head"] = "newer_bar"
    lst["tail.tail.head"] = "newer_baz"

    assert lst["head"] == "newer_foo"
    assert lst["tail.head"] == "newer_bar"
    assert lst["tail.tail.head"] == "newer_baz"


Creating types and adding features
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    from cassis import *

    typesystem = TypeSystem()

    parent_type = typesystem.create_type(name='example.ParentType')
    typesystem.create_feature(domainType=parent_type, name='parentFeature', rangeType=TYPE_NAME_STRING)

    child_type = typesystem.create_type(name='example.ChildType', supertypeName=parent_type.name)
    typesystem.create_feature(domainType=child_type, name='childFeature', rangeType=TYPE_NAME_INTEGER)

    annotation = child_type(parentFeature='parent', childFeature='child')

When adding new features, these changes are propagated. For example,
adding a feature to a parent type makes it available to a child type.
Therefore, the type system does not need to be frozen for consistency.
The type system can be changed even after loading, it is not frozen
like in UIMAj.

Sofa support
~~~~~~~~~~~~

A Sofa represents some form of an unstructured artifact that is processed in a UIMA pipeline. It contains for instance
the document text. Currently, new Sofas can be created. This is automatically done when creating a new view. Basic
properties of the Sofa can be read and written:

.. code:: python

    cas = Cas()
    cas.sofa_string = "Joe waited for the train . The train was late ."
    cas.sofa_mime = "text/plain"

    print(cas.sofa_string)
    print(cas.sofa_mime)

Array support
~~~~~~~~~~~~~

Array feature values are not simply Python arrays, but they are wrapped in a feature structure of
a UIMA array type such as :code:`uima.cas.FSArray`.

.. code:: python

    from cassis import *
    from cassis.typesystem import TYPE_NAME_FS_ARRAY, TYPE_NAME_ANNOTATION

    typesystem = TypeSystem()

    ArrayHolder = typesystem.create_type(name='example.ArrayHolder')
    typesystem.create_feature(domainType=ArrayHolder, name='array', rangeType=TYPE_NAME_FS_ARRAY)

    cas = Cas(typesystem=typesystem)

    Annotation = cas.typesystem.get_type(TYPE_NAME_ANNOTATION)
    FSArray = cas.typesystem.get_type(TYPE_NAME_FS_ARRAY)

    ann = Annotation(begin=0, end=1)
    cas.add(ann1)
    holder = ArrayHolder(array=FSArray(elements=[ann, ann, ann]))
    cas.add(holder)

Managing views
~~~~~~~~~~~~~~

A view into a CAS contains a subset of feature structures and annotations. One view corresponds to exactly one Sofa. It
can also be used to query and alter information about the Sofa, e.g. the document text. Annotations added to one view
are not visible in another view.  A view Views can be created and changed. A view has the same methods and attributes
as a :code:`Cas` .

.. code:: python

    from cassis import *

    with open('typesystem.xml', 'rb') as f:
        typesystem = load_typesystem(f)
    Token = typesystem.get_type('cassis.Token')

    # This creates automatically the view `_InitialView`
    cas = Cas()
    cas.sofa_string = "I like cheese ."

    cas.add_all([
        Token(begin=0, end=1),
        Token(begin=2, end=6),
        Token(begin=7, end=13),
        Token(begin=14, end=15)
    ])

    print([x.get_covered_text() for x in cas.select_all()])

    # Create a new view and work on it.
    view = cas.create_view('testView')
    view.sofa_string = "I like blackcurrant ."

    view.add_all([
        Token(begin=0, end=1),
        Token(begin=2, end=6),
        Token(begin=7, end=19),
        Token(begin=20, end=21)
    ])

    print([x.get_covered_text() for x in view.select_all()])

Merging type systems
~~~~~~~~~~~~~~~~~~~~

Sometimes, it is desirable to merge two type systems. With **cassis**, this can be
achieved via the :code:`merge_typesystems` function. The detailed rules of merging can be found
`here <https://uima.apache.org/d/uimaj-2.10.4/references.html#ugr.ref.cas.typemerging>`_.

.. code:: python

    from cassis import *

    with open('typesystem.xml', 'rb') as f:
        typesystem = load_typesystem(f)

    ts = merge_typesystems([typesystem, load_dkpro_core_typesystem()])

Type checking
~~~~~~~~~~~~~

When adding annotations, no type checking is performed for simplicity reasons.
In order to check types, call the :code:`cas.typecheck()` method. Currently, it only
checks whether elements in `uima.cas.FSArray` are
adhere to the specified :code:`elementType`.

DKPro Core Integration
----------------------

A CAS using the DKPro Core Type System can be created via

.. code:: python

    from cassis import *

    cas = Cas(typesystem=load_dkpro_core_typesystem())

    for t in cas.typesystem.get_types():
        print(t)

Miscellaneous
-------------

If feature names clash with Python magic variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If your type system defines a type called :code:`self` or :code:`type`, then it will be made
available as a member variable :code:`self_` or :code:`type_` on the respective type:

.. code:: python

    from cassis import *
    from cassis.typesystem import *

    typesystem = TypeSystem()

    ExampleType = typesystem.create_type(name='example.Type')
    typesystem.create_feature(domainType=ExampleType, name='self', rangeType=TYPE_NAME_STRING)
    typesystem.create_feature(domainType=ExampleType, name='type', rangeType=TYPE_NAME_STRING)

    annotation = ExampleType(self_="Test string1", type_="Test string2")

    print(annotation.self_)
    print(annotation.type_)

Leniency
~~~~~~~~

If the type for a feature structure is not found in the typesystem, it will raise an exception by default.
If you want to ignore these kind of errors, you can pass :code:`lenient=True` to the :code:`Cas` constructor or
to :code:`load_cas_from_xmi`.

Large XMI files
~~~~~~~~~~~~~~~

If you try to parse large XMI files and get an error message like :code:`XMLSyntaxError: internal error: Huge input lookup`,
then you can disable this security check by passing :code:`trusted=True` to your calls to :code:`load_cas_from_xmi`.

Citing & Authors
----------------

If you find this repository helpful, feel free to cite

.. code:: bibtex

    @software{klie2020_cassis,
      author       = {Jan-Christoph Klie and
                      Richard Eckart de Castilho},
      title        = {DKPro Cassis - Reading and Writing UIMA CAS Files in Python},
      publisher    = {Zenodo},
      doi          = {10.5281/zenodo.3994108},
      url          = {https://github.com/dkpro/dkpro-cassis}
    }

Development
-----------

The required dependencies are managed by **pip**. A virtual environment
containing all needed packages for development and production can be
created and activated by

::

    virtualenv venv --python=python3 --no-site-packages
    source venv/bin/activate
    pip install -e ".[test, dev, doc]"

The tests can be run in the current environment by invoking

::

    make test

or in a clean environment via

::

    tox

Release
-------

- Make sure all issues for the milestone are completed, otherwise move them to the next
- Checkout the ``main`` branch
- Bump the version in ``cassis/__version__.py`` to a stable one, e.g. ``__version__ = "0.6.0"``, commit and push, wait until the build completed. An example commit message would be ``No issue. Release 0.6.0``
- Create a tag for that version via e.g. ``git tag v0.6.0`` and push the tags via ``git push --tags``. Pushing a tag triggers the release to pypi
- Bump the version in ``cassis/__version__.py`` to the next development version, e.g. ``0.7.0-dev``, commit and push that. An example commit message would be ``No issue. Bump version after release``
- Once the build has completed and pypi accepted the new version, go to the Github release and write the changelog based on the issues in the respective milestone
- Create a new milestone for the next version

