import pathlib

# The marker that ``docs/index.md`` uses in its ``{include} ../README.md``
# directive via ``:start-after:``. If the README heading changes, the Sphinx
# include silently breaks, so we guard the contract here.
README_START_AFTER_MARKER = "# dkpro-cassis"


def test_readme_exists_and_is_non_empty():
    parent = pathlib.Path(__file__).parent.resolve().parent
    readme = parent / "README.md"

    assert readme.is_file(), "README.md is missing"
    assert readme.read_text(encoding="utf-8").strip(), "README.md is empty"


def test_readme_contains_docs_include_marker():
    parent = pathlib.Path(__file__).parent.resolve().parent
    readme = parent / "README.md"

    content = readme.read_text(encoding="utf-8")
    assert README_START_AFTER_MARKER in content, (
        f"README.md must contain the marker '{README_START_AFTER_MARKER}' that "
        "docs/index.md relies on for its include directive"
    )
