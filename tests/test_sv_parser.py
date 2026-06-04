"""Unit tests for the generic SystemVerilog parser (lib/sv_parser.py).

All tests use inline SV snippets — no dependency on real project files.
"""

from pathlib import Path

from lib.sv_parser import (
    SVClassInfo,
    classify_uvm_role,
    extract_classes,
    extract_config_db_usage,
    extract_config_knobs,
    extract_methods,
    extract_modules,
    extract_plusargs,
    infer_feature_tags,
    link_tests_to_sequences,
    parse_directory,
    parse_sv_file,
    resolve_extends_chain,
)


class TestExtractClasses:
    """Tests for class extraction."""

    def test_extract_class_simple(self) -> None:
        sv = "class my_class;\nendclass\n"
        classes = extract_classes(sv, file="test.sv")
        assert len(classes) == 1
        assert classes[0].name == "my_class"
        assert classes[0].extends is None
        assert classes[0].file == "test.sv"

    def test_extract_class_with_extends(self) -> None:
        sv = "class child_class extends parent_class;\nendclass\n"
        classes = extract_classes(sv)
        assert len(classes) == 1
        assert classes[0].name == "child_class"
        assert classes[0].extends == "parent_class"

    def test_extract_class_with_parameterization(self) -> None:
        sv = "class my_seq extends uvm_sequence #(my_item);\nendclass\n"
        classes = extract_classes(sv)
        assert len(classes) == 1
        assert classes[0].name == "my_seq"
        assert classes[0].extends == "uvm_sequence"

    def test_uvm_component_utils_macro(self) -> None:
        sv = (
            "class my_env extends uvm_env;\n"
            "  `uvm_component_utils(my_env)\n"
            "endclass\n"
        )
        classes = extract_classes(sv)
        assert len(classes) == 1
        assert classes[0].utils_macro == "uvm_component_utils"

    def test_uvm_object_utils_macro(self) -> None:
        sv = (
            "class my_config extends uvm_object;\n"
            "  `uvm_object_utils(my_config)\n"
            "endclass\n"
        )
        classes = extract_classes(sv)
        assert len(classes) == 1
        assert classes[0].utils_macro == "uvm_object_utils"

    def test_multiple_classes(self) -> None:
        sv = (
            "class class_a;\nendclass\n"
            "class class_b extends class_a;\nendclass\n"
            "class class_c;\nendclass\n"
        )
        classes = extract_classes(sv)
        assert len(classes) == 3
        assert [c.name for c in classes] == ["class_a", "class_b", "class_c"]
        assert classes[1].extends == "class_a"


class TestExtractMethods:
    """Tests for task/function extraction."""

    def test_extract_task(self) -> None:
        sv = "task run_phase(uvm_phase phase);\nendtask\n"
        methods = extract_methods(sv)
        assert len(methods) == 1
        assert methods[0].name == "run_phase"
        assert methods[0].is_task is True
        assert methods[0].is_virtual is False

    def test_extract_function(self) -> None:
        sv = "function void build_phase(uvm_phase phase);\nendfunction\n"
        methods = extract_methods(sv)
        assert len(methods) == 1
        assert methods[0].name == "build_phase"
        assert methods[0].is_task is False

    def test_extract_virtual_task(self) -> None:
        sv = "virtual task my_task(int a, int b);\nendtask\n"
        methods = extract_methods(sv)
        assert len(methods) == 1
        assert methods[0].is_virtual is True
        assert methods[0].is_task is True
        assert methods[0].name == "my_task"

    def test_extract_multiline_method(self) -> None:
        sv = "task automatic body(\n  input int count,\n  output bit done\n);\nendtask\n"
        methods = extract_methods(sv)
        assert len(methods) == 1
        assert methods[0].name == "body"
        assert "count" in methods[0].signature

    def test_extract_function_with_return_type(self) -> None:
        sv = "function int get_count();\n  return count;\nendfunction\n"
        methods = extract_methods(sv)
        assert len(methods) == 1
        assert methods[0].name == "get_count"
        assert methods[0].return_type == "int"


class TestExtractModules:
    """Tests for module extraction."""

    def test_extract_module(self) -> None:
        sv = "module top(input clk, output data);\nendmodule\n"
        modules = extract_modules(sv, file="top.sv")
        assert len(modules) == 1
        assert modules[0].name == "top"
        assert modules[0].file == "top.sv"

    def test_extract_module_with_parameters(self) -> None:
        sv = (
            "module fifo #(parameter int DEPTH = 16, parameter int WIDTH = 32)"
            "(input clk);\nendmodule\n"
        )
        modules = extract_modules(sv)
        assert len(modules) == 1
        assert modules[0].name == "fifo"
        assert len(modules[0].parameters) == 2
        assert modules[0].parameters[0]["name"] == "DEPTH"

    def test_extract_ports(self) -> None:
        sv = "module dut(input clk, input rst_n, output [31:0] data, inout sda);\nendmodule\n"
        modules = extract_modules(sv)
        assert len(modules) == 1
        port_names = [p.split()[-1] for p in modules[0].ports]
        assert "clk" in port_names
        assert "rst_n" in port_names
        assert "data" in port_names
        assert "sda" in port_names

    def test_extract_fsm_enum(self) -> None:
        sv = (
            "module fsm_mod(input clk);\n"
            "  typedef enum logic [1:0] {IDLE, RUN, DONE, ERROR} state_t;\n"
            "endmodule\n"
        )
        modules = extract_modules(sv)
        assert len(modules) == 1
        assert "IDLE" in modules[0].fsm_states
        assert "RUN" in modules[0].fsm_states
        assert "DONE" in modules[0].fsm_states
        assert "ERROR" in modules[0].fsm_states


class TestConfigDbAndPlusargs:
    """Tests for config_db and plusarg extraction."""

    def test_extract_config_db_usage(self) -> None:
        sv = (
            'uvm_config_db #(virtual axi_intf)::set(this, "*", "vif", vif);\n'
            'uvm_config_db #(axi2ahb_config)::get(this, "", "cfg", cfg);\n'
        )
        usage = extract_config_db_usage(sv)
        assert len(usage) == 2
        assert usage[0]["kind"] == "set"
        assert usage[1]["kind"] == "get"

    def test_extract_plusargs(self) -> None:
        sv = (
            'void\'(uvm_cmdline_proc.get_arg_value("+NUM_CH=", num_ch_str));\n'
            'void\'($value$plusargs("TIMEOUT=%d", timeout));\n'
        )
        plusargs = extract_plusargs(sv)
        names = [p["name"] for p in plusargs]
        assert "NUM_CH" in names
        assert "TIMEOUT" in names


class TestFeatureTags:
    """Tests for heuristic feature tag inference."""

    def test_infer_feature_tags(self) -> None:
        tags = infer_feature_tags("burst_write_seq", "burst_write_seq.sv")
        assert "burst" in tags
        assert "write" in tags

    def test_infer_feature_tags_multiple(self) -> None:
        tags = infer_feature_tags("random_mixed_traffic_test", "random_mixed_traffic_test.sv")
        assert "random" in tags
        assert "mixed" in tags
        assert "traffic" in tags

    def test_infer_feature_tags_empty(self) -> None:
        tags = infer_feature_tags("base_test", "base_test.sv")
        assert tags == []

    def test_infer_feature_tags_from_body(self) -> None:
        tags = infer_feature_tags("my_seq", "my_seq.sv", body="send_burst read_data error_check")
        assert "burst" in tags
        assert "read" in tags
        assert "error" in tags

    def test_infer_feature_tags_deduplication(self) -> None:
        tags = infer_feature_tags("write_write_seq", "write_write_seq.sv", body="write write write")
        assert tags.count("write") == 1


class TestExtendsChainAndRole:
    """Tests for extends chain resolution and UVM role classification."""

    def test_resolve_extends_chain(self) -> None:
        classes = [
            SVClassInfo(name="test_a", file="", extends="base_test", utils_macro=None),
            SVClassInfo(name="base_test", file="", extends="uvm_test", utils_macro=None),
            SVClassInfo(name="my_seq", file="", extends="uvm_sequence", utils_macro=None),
        ]
        chains = resolve_extends_chain(classes)
        assert chains["test_a"] == ["base_test", "uvm_test"]
        assert chains["base_test"] == ["uvm_test"]
        assert chains["my_seq"] == ["uvm_sequence"]

    def test_classify_uvm_role(self) -> None:
        classes = [
            SVClassInfo(
                name="my_test", file="", extends="uvm_test",
                utils_macro="uvm_component_utils",
            ),
            SVClassInfo(
                name="my_seq", file="", extends="uvm_sequence",
                utils_macro="uvm_object_utils",
            ),
            SVClassInfo(
                name="my_env", file="", extends="uvm_env",
                utils_macro="uvm_component_utils",
            ),
            SVClassInfo(
                name="my_driver", file="", extends="uvm_driver",
                utils_macro="uvm_component_utils",
            ),
            SVClassInfo(
                name="my_config", file="", extends="uvm_object",
                utils_macro="uvm_object_utils",
            ),
        ]
        chains = resolve_extends_chain(classes)
        assert classify_uvm_role(classes[0], chains) == "test"
        assert classify_uvm_role(classes[1], chains) == "sequence"
        assert classify_uvm_role(classes[2], chains) == "env"
        assert classify_uvm_role(classes[3], chains) == "driver"
        assert classify_uvm_role(classes[4], chains) == "object"

    def test_classify_indirect_role(self) -> None:
        """A class extending a class extending uvm_test should be 'test'."""
        classes = [
            SVClassInfo(
                name="base_test", file="", extends="uvm_test",
                utils_macro="uvm_component_utils",
            ),
            SVClassInfo(
                name="concrete_test", file="", extends="base_test",
                utils_macro="uvm_component_utils",
            ),
        ]
        chains = resolve_extends_chain(classes)
        assert classify_uvm_role(classes[1], chains) == "test"

    def test_classify_unknown_role(self) -> None:
        cls = SVClassInfo(
            name="random_class", file="", extends=None,
            utils_macro="uvm_component_utils",
        )
        chains = resolve_extends_chain([cls])
        assert classify_uvm_role(cls, chains) == "unknown"


class TestLinkTestsToSequences:
    """Tests for test-to-sequence linking."""

    def test_link_via_type_reference(self) -> None:
        test_cls = SVClassInfo(
            name="my_test", file="tests/my_test.sv",
            extends="base_test", utils_macro=None,
        )
        seq_cls = SVClassInfo(
            name="my_seq", file="seq/my_seq.sv",
            extends="uvm_sequence", utils_macro=None,
        )
        raw_texts = {
            "tests/my_test.sv": (
                "class my_test extends base_test;\n"
                "  my_seq seq;\n"
                "  task run_phase(uvm_phase phase);\n"
                "    seq = my_seq::type_id::create(\"seq\");\n"
                "    seq.start(null);\n"
                "  endtask\n"
                "endclass\n"
            ),
        }
        links = link_tests_to_sequences([test_cls], [seq_cls], raw_texts)
        assert "my_seq" in links["my_test"]

    def test_link_no_match(self) -> None:
        test_cls = SVClassInfo(
            name="empty_test", file="tests/empty_test.sv",
            extends="base_test", utils_macro=None,
        )
        seq_cls = SVClassInfo(
            name="other_seq", file="seq/other_seq.sv",
            extends="uvm_sequence", utils_macro=None,
        )
        raw_texts = {
            "tests/empty_test.sv": "class empty_test extends base_test;\nendclass\n",
        }
        links = link_tests_to_sequences([test_cls], [seq_cls], raw_texts)
        assert links["empty_test"] == []


class TestExtractConfigKnobs:
    """Tests for config knob extraction."""

    def test_extract_config_knobs(self) -> None:
        config_cls = SVClassInfo(
            name="my_config",
            file="config/my_config.sv",
            extends="uvm_object",
            utils_macro="uvm_object_utils",
        )
        raw_texts = {
            "config/my_config.sv": (
                "class my_config extends uvm_object;\n"
                "  int timeout = 1000;\n"
                "  bit enable_coverage = 1;\n"
                "  string mode = \"normal\";\n"
                "endclass\n"
            ),
        }
        knobs = extract_config_knobs([config_cls], raw_texts)
        knob_names = [k["name"] for k in knobs]
        assert "timeout" in knob_names
        assert "enable_coverage" in knob_names
        assert "mode" in knob_names


class TestFileParsing:
    """Tests for file and directory parsing."""

    def test_parse_sv_file(self, tmp_path: Path) -> None:
        sv_file = tmp_path / "test.sv"
        sv_file.write_text(
            "class my_class extends uvm_test;\n"
            "  `uvm_component_utils(my_class)\n"
            "  task run_phase(uvm_phase phase);\n"
            "  endtask\n"
            "endclass\n",
            encoding="utf-8",
        )
        result = parse_sv_file(sv_file, project_root=tmp_path)
        assert len(result.classes) == 1
        assert result.classes[0].name == "my_class"
        assert result.file == "test.sv"

    def test_parse_sv_file_nonexistent(self, tmp_path: Path) -> None:
        result = parse_sv_file(tmp_path / "nonexistent.sv", project_root=tmp_path)
        assert result.classes == []
        assert result.modules == []

    def test_parse_directory(self, tmp_path: Path) -> None:
        sub = tmp_path / "src"
        sub.mkdir()
        (sub / "a.sv").write_text("class a;\nendclass\n", encoding="utf-8")
        (sub / "b.svh").write_text("class b extends a;\nendclass\n", encoding="utf-8")
        (sub / "c.txt").write_text("not a sv file", encoding="utf-8")

        results = parse_directory(sub, project_root=tmp_path)
        assert len(results) == 2
        all_classes = [cls for pf in results for cls in pf.classes]
        assert len(all_classes) == 2

    def test_parse_directory_nonexistent(self, tmp_path: Path) -> None:
        results = parse_directory(tmp_path / "nonexistent", project_root=tmp_path)
        assert results == []
