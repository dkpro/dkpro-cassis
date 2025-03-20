import pathlib

from rstcheck_core import checker


def test_readme_is_proper_rst():
    parent = pathlib.Path(__file__).parent.resolve().parent
    path_to_readme = parent / "README.rst"

    with path_to_readme.open() as f:
        rst = f.read()

    errors = [str(e) for e in list(checker.check_source(rst))]
    # https://github.com/rstcheck/rstcheck-core/issues/4
    errors = [s for s in errors if not ("Hyperlink target" in s and "is not referenced." in s)]
    assert len(errors) == 0, "; ".join(errors)
