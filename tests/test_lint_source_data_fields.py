"""Verify the source_data_fields ⊆ index.fields lint check."""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import textwrap

ROOT = pathlib.Path(__file__).resolve().parent.parent
LINT_PATH = ROOT / "scripts" / "accelerator-lint.py"


def _load_lint():
    spec = importlib.util.spec_from_file_location("acc_lint", LINT_PATH)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec and spec.loader
    sys.modules["acc_lint"] = mod
    spec.loader.exec_module(mod)
    return mod


SCHEMA_TEMPLATE = textwrap.dedent('''
    from azure.search.documents.indexes.models import (
        SearchIndex, SimpleField, SearchableField, SearchField,
        SearchFieldDataType,
    )

    def index_definition(name: str) -> SearchIndex:
        return SearchIndex(
            name=name,
            fields=[
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SearchableField(name="content", type=SearchFieldDataType.String),
                SimpleField(name="source", type=SearchFieldDataType.String),
                SearchableField(name="company_name", type=SearchFieldDataType.String),
            ],
        )
''')


def test_extract_returns_field_names_from_searchindex_call(tmp_path):
    lint = _load_lint()
    p = tmp_path / "retrieval.py"
    p.write_text(SCHEMA_TEMPLATE, encoding="utf-8")
    names = lint._ast_extract_field_names(p, "index_definition")
    assert names == {"id", "content", "source", "company_name"}


def test_extract_returns_none_when_function_missing(tmp_path):
    lint = _load_lint()
    p = tmp_path / "retrieval.py"
    p.write_text("def other(): pass\n", encoding="utf-8")
    assert lint._ast_extract_field_names(p, "index_definition") is None


def test_extract_returns_none_when_file_missing(tmp_path):
    lint = _load_lint()
    assert lint._ast_extract_field_names(tmp_path / "missing.py", "x") is None


def test_extract_handles_no_searchindex_call(tmp_path):
    lint = _load_lint()
    p = tmp_path / "retrieval.py"
    p.write_text(
        "def index_definition(name):\n    return None\n",
        encoding="utf-8",
    )
    assert lint._ast_extract_field_names(p, "index_definition") is None


def test_extract_handles_attribute_call_form(tmp_path):
    """``module.SearchIndex(...)`` should also be recognised."""
    lint = _load_lint()
    p = tmp_path / "retrieval.py"
    p.write_text(textwrap.dedent('''
        from azure.search.documents.indexes import models

        def index_definition(name):
            return models.SearchIndex(
                name=name,
                fields=[
                    models.SimpleField(name="id"),
                    models.SimpleField(name="title"),
                ],
            )
    '''), encoding="utf-8")
    names = lint._ast_extract_field_names(p, "index_definition")
    assert names == {"id", "title"}


def test_extract_ignores_non_string_name_kwargs(tmp_path):
    lint = _load_lint()
    p = tmp_path / "retrieval.py"
    p.write_text(textwrap.dedent('''
        def index_definition(name):
            return SearchIndex(
                name=name,
                fields=[
                    SimpleField(name="ok"),
                    SimpleField(name=variable_name),
                    SimpleField(),
                ],
            )
    '''), encoding="utf-8")
    names = lint._ast_extract_field_names(p, "index_definition")
    assert names == {"ok"}
