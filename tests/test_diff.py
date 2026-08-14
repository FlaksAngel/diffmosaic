from diffmosaic.diff import parse_unified_diff


def test_parse_unified_diff_extracts_paths_and_hunks() -> None:
    diff = """diff --git a/src/example.py b/src/example.py
index 1111111..2222222 100644
--- a/src/example.py
+++ b/src/example.py
@@ -4,2 +4,3 @@ def total():
-    return subtotal
+    if discount:
+        return subtotal - discount
+    return subtotal
"""

    deltas = parse_unified_diff(diff)

    assert len(deltas) == 1
    delta = deltas[0]
    assert delta.old_path == "src/example.py"
    assert delta.new_path == "src/example.py"
    assert delta.changed_new_lines == (4, 5, 6)
    assert delta.changed_old_lines == 1


def test_parse_unified_diff_preserves_zero_line_insertions() -> None:
    diff = """diff --git a/new.py b/new.py
new file mode 100644
--- /dev/null
+++ b/new.py
@@ -0,0 +1,2 @@
+one = 1
+two = 2
"""

    delta = parse_unified_diff(diff)[0]

    assert delta.old_path is None
    assert delta.new_path == "new.py"
    assert delta.changed_new_lines == (1, 2)
