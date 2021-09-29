import pathlib

import rstcheck


def test_readme_is_proper_rst():
    parent = pathlib.Path(__file__).parent.resolve().parent
    path_to_readme = parent / "README.rst"

    with path_to_readme.open() as f:
        rst = f.read()

    errors = list(rstcheck.check(rst))
    assert len(errors) == 0, "; ".join(str(e) for e in errors)
