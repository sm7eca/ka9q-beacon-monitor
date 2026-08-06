# M4.8 Finding Disposition

## M4.8-F-001 — CLOSED

The Web UI now escapes every literal `<` in serialized configuration JSON as `\u003c` before embedding it in the `application/json` script element. This preserves valid JSON while preventing a configured `</script>` sequence from terminating the element.

Verification is provided by `test_embedded_config_json_blocks_script_tag_breakout`, which checks both the generated HTML and successful JSON decoding.
