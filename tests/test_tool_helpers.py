"""Tests for mcp_core.tool_helpers — pure functions, no mocking needed."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from mcp_core.tool_helpers import (
    sanitize_csharp_code,
    check_paracore_compliance,
    check_dangerous_patterns,
    check_suspicious_param_names,
    _suggest_paracore_fix,
)


# ── sanitize_csharp_code ──────────────────────────────────────────────────

class TestSanitize:
    def test_strips_bracket_annotations(self):
        assert sanitize_csharp_code('"Level [String]"') == '"Level"'
        assert sanitize_csharp_code('"Area [Double]"') == '"Area"'
        assert sanitize_csharp_code('"Volume [Double]"') == '"Volume"'

    def test_strips_paren_annotations(self):
        assert sanitize_csharp_code('"Level (String)"') == '"Level"'

    def test_preserves_valid_strings(self):
        assert sanitize_csharp_code('"Fire Rating"') == '"Fire Rating"'
        assert sanitize_csharp_code('"Level"') == '"Level"'

    def test_handles_multiple_annotations(self):
        code = '.WhereParam("Level [String]", "Level 1").GetNum("Area [Double]", "m2")'
        result = sanitize_csharp_code(code)
        assert '"Level [String]"' not in result
        assert '"Area [Double]"' not in result
        assert '"Level"' in result
        assert '"Area"' in result


# ── check_paracore_compliance ─────────────────────────────────────────────

class TestParacoreCompliance:
    def test_blocks_filtered_element_collector(self):
        err = check_paracore_compliance("new FilteredElementCollector(Doc)")
        assert err is not None
        assert "GetElements" in err

    def test_blocks_lookup_parameter(self):
        err = check_paracore_compliance('el.LookupParameter("Name")')
        assert err is not None
        assert "GetStr" in err

    def test_blocks_get_parameter(self):
        err = check_paracore_compliance('el.get_Parameter("Name")')
        assert err is not None
        assert "GetStr" in err

    def test_blocks_console_writeline(self):
        err = check_paracore_compliance("Console.WriteLine(msg)")
        assert err is not None
        assert "Println" in err

    def test_blocks_foreach_println(self):
        err = check_paracore_compliance(
            'foreach(var x in items) { Println(x.Name); }'
        )
        assert err is not None
        assert "Table" in err

    def test_blocks_select_after_groupbyparam(self):
        err = check_paracore_compliance(
            'GetElements("Walls").GroupByParam("Level").Select(g => new{})'
        )
        assert err is not None
        assert "Table" in err

    def test_blocks_hardcoded_unit_math(self):
        err = check_paracore_compliance("var x = value / 304.8;")
        assert err is not None
        assert "unit" in err.lower()

    def test_blocks_lowercase_doc(self):
        err = check_paracore_compliance("doc.ProjectInformation")
        assert err is not None
        assert "Doc" in err

    def test_blocks_orderby_lambda(self):
        err = check_paracore_compliance(
            "elements.OrderBy(e => e.GetNum(\"Area\"))"
        )
        assert err is not None
        assert "OrderByParam" in err

    def test_blocks_sum_lambda(self):
        err = check_paracore_compliance(
            "elements.Sum(e => e.GetNum(\"Area\", \"m2\"))"
        )
        assert err is not None
        assert "SumParam" in err

    def test_blocks_transact_without_name(self):
        err = check_paracore_compliance("Transact(() => { wall.Delete(); })")
        assert err is not None
        assert "name string" in err.lower()

    def test_blocks_combinedparams_with_args(self):
        err = check_paracore_compliance(
            'el.CombinedParams("filter").Table()'
        )
        assert err is not None
        assert "NO arguments" in err

    def test_blocks_setval_on_collection(self):
        err = check_paracore_compliance(
            'GetElements("Walls").WhereParam("Fire Rating","None").SetVal("Comments","X")'
        )
        assert err is not None

    def test_allows_valid_code(self):
        assert check_paracore_compliance(
            'GetElements("Walls").WhereParam("Fire Rating", "2 hr").Table()'
        ) is None

    def test_allows_getstr_getnum(self):
        assert check_paracore_compliance(
            'el.GetStr("Name"); el.GetNum("Area", "m2")'
        ) is None

    def test_allows_groupbyparam_then_table(self):
        assert check_paracore_compliance(
            'GetElements("Walls").GroupByParam("Level").Table()'
        ) is None


# ── check_dangerous_patterns ──────────────────────────────────────────────

class TestDangerousPatterns:
    def test_blocks_process_start(self):
        err = check_dangerous_patterns("Process.Start(\"cmd.exe\")")
        assert err is not None
        assert "Process.Start" in err

    def test_blocks_environment_exit(self):
        err = check_dangerous_patterns("Environment.Exit(0)")
        assert err is not None

    def test_blocks_registry_access(self):
        err = check_dangerous_patterns("Microsoft.Win32.Registry")
        assert err is not None

    def test_blocks_assembly_load(self):
        err = check_dangerous_patterns("Assembly.Load(byteArray)")
        assert err is not None

    def test_blocks_file_delete(self):
        err = check_dangerous_patterns("File.Delete(\"test.txt\")")
        assert err is not None

    def test_blocks_httpclient_agent_only(self):
        err = check_dangerous_patterns("new HttpClient()", agent_only=True)
        assert err is not None
        assert "RestSharp" in err

    def test_allows_httpclient_when_not_agent(self):
        assert check_dangerous_patterns("new HttpClient()", agent_only=False) is None

    def test_allows_safe_code(self):
        assert check_dangerous_patterns(
            'GetElements("Walls").Table()'
        ) is None


# ── check_suspicious_param_names ──────────────────────────────────────────

class TestSuspiciousParamNames:
    def test_flags_fabricated_pascalcase(self):
        # Not in any schema cache — should warn
        warn = check_suspicious_param_names(
            'GetElements("Walls").WhereParam("FireRating", "2 hr")'
        )
        assert "FireRating" in warn
        assert "no spaces" in warn.lower()

    def test_passes_single_word_params(self):
        assert check_suspicious_param_names('GetNum("Volume", "m3")') == ""
        assert check_suspicious_param_names('GetStr("Mark")') == ""
        assert check_suspicious_param_names('GetStr("Length")') == ""

    def test_passes_space_separated_params(self):
        assert check_suspicious_param_names(
            'WhereParam("Fire Rating", "2 hr")'
        ) == ""

    def test_silences_if_in_schema_cache(self):
        from mcp_core.schema_cache import _cache as schema_cache
        # Populate cache with a known PascalCase param
        schema_cache["Doors"] = [
            {"name": "IfcGUID", "storage_type": "String", "is_type": False},
            {"name": "StopDepth", "storage_type": "Double", "is_type": True},
        ]
        warn = check_suspicious_param_names(
            'GetElements("Doors").GetStr("IfcGUID")'
        )
        assert warn == ""  # silently passes — it's a real param

    def test_returns_empty_for_no_quoted_strings(self):
        assert check_suspicious_param_names("var x = 5;") == ""


# ── _suggest_paracore_fix ─────────────────────────────────────────────────

class TestSuggestParacoreFix:
    def test_suggests_whereparam_for_where_error(self):
        suggestion = _suggest_paracore_fix(
            "does not contain a definition for 'Where'"
        )
        assert suggestion is not None
        assert "WhereParam" in suggestion

    def test_suggests_orderbyparam_for_orderby_error(self):
        suggestion = _suggest_paracore_fix(
            "does not contain a definition for 'OrderBy'"
        )
        assert suggestion is not None
        assert "OrderByParam" in suggestion

    def test_suggests_getstr_for_lookupparameter_error(self):
        suggestion = _suggest_paracore_fix(
            "'LookupParameter' is not"
        )
        assert suggestion is not None
        assert "GetStr" in suggestion

    def test_suggests_doc_for_lowercase_doc_error(self):
        suggestion = _suggest_paracore_fix(
            "The name 'doc' does not exist"
        )
        assert suggestion is not None
        assert "Doc" in suggestion

    def test_suggests_getelements_for_filteredelementcollector(self):
        suggestion = _suggest_paracore_fix(
            "FilteredElementCollector is not"
        )
        assert suggestion is not None
        assert "GetElements" in suggestion

    def test_suggests_println_for_console_error(self):
        suggestion = _suggest_paracore_fix("'Console' does not exist")
        assert suggestion is not None
        assert "Println" in suggestion

    def test_maps_multiple_suggestions(self):
        suggestion = _suggest_paracore_fix(
            "does not contain a definition for 'Where' and 'OrderBy'"
        )
        assert suggestion is not None
        assert "WhereParam" in suggestion or "OrderByParam" in suggestion

    def test_returns_none_for_unknown_error(self):
        assert _suggest_paracore_fix("some random error text") is None
