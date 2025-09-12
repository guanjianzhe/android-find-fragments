import unittest

from tools.aff_cli import (
    parse_activity_component_from_dumpsys,
    parse_fragments_from_dumpsys,
)


ANDROID11_SAMPLE = """
  mResumedActivity: ActivityRecord{2baae81 u0 com.example.app/.ui.MainActivity t2431 d0}
""".strip()


ANDROID14_SAMPLE = """
  topResumedActivity=ActivityRecord{77b3dc7 u0 com.example.app/.ui.MainActivity t90}
""".strip()


FRAGMENTS_SAMPLE = """
Added Fragments:
  #0 com.example.app.ui.HomeFragment{123456}
  #1 com.example.app.ui.child.ChildFragment{abcdef}
AutofillManager:
""".strip()


class TestParsers(unittest.TestCase):
    def test_parse_activity_11(self):
        comp = parse_activity_component_from_dumpsys(ANDROID11_SAMPLE, prefer_top=False)
        self.assertEqual(comp, "com.example.app/.ui.MainActivity")

    def test_parse_activity_14(self):
        comp = parse_activity_component_from_dumpsys(ANDROID14_SAMPLE, prefer_top=True)
        self.assertEqual(comp, "com.example.app/.ui.MainActivity")

    def test_parse_fragments(self):
        frags = parse_fragments_from_dumpsys(FRAGMENTS_SAMPLE)
        self.assertEqual(frags, ["HomeFragment", "ChildFragment"])


if __name__ == "__main__":
    unittest.main()
