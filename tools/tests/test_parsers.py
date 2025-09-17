import unittest

from tools.acf_cli import (
    parse_activity_component_from_dumpsys,
    parse_fragments_from_dumpsys,
    parse_fragments_from_dumpsys_strict,
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
  #2 com.example.app.ui.dialog.InfoDialogFragment{789abc}
AutofillManager:
""".strip()

FRAGMENTS_ACTIVE_SAMPLE = """
Active Fragments:
  #0: com.example.app.ui.TabFragment{000000}
  #1: NestedChildFragment{111111}
  #2: com.example.app.ui.list.ListFragment{222222}
Back Stack:
""".strip()

FRAGMENTS_COMPLEX_SAMPLE = """
Added Fragments:
  #0 com.example.app.ui.HomeFragment{123456}
  #1: com.example.app.ui.child.ChildFragment{abcdef}
  #2 com.example.app.ui.dialog.InfoDialogFragment{789abc}
  #3: NestedChildFragment{111111}
  #4 com.example.app.ui.tab.TabFragment{000000}
  ReportFragment{system}
  SupportRequestManagerFragment{system}
  AutofillManager:
""".strip()

FRAGMENTS_ANDROID_SYSTEM_SAMPLE = """
Added Fragments:
  #0 com.example.app.ui.HomeFragment{123456}
  #1: com.example.app.ui.child.ChildFragment{abcdef}
  DialogFragment{system}
  ListFragment{system}
  PreferenceFragment{system}
  WebViewFragment{system}
  Fragment{system}
  androidx.fragment.app.Fragment{system}
  android.app.Fragment{system}
  AutofillManager:
""".strip()

FULL_DUMPSYS_SAMPLE = """
ACTIVITY MANAGER ACTIVITIES (dumpsys activity activities)
Stack #0:
  Task #123:
    Activity #1: com.other.app/.OtherActivity
      Added Fragments:
        #0 com.other.app.ui.OtherFragment{111111}
      AutofillManager:
    Activity #2: com.example.app/.ui.MainActivity
      Added Fragments:
        #0 com.example.app.ui.HomeFragment{123456}
        #1 com.example.app.ui.ProfileFragment{789abc}
      AutofillManager:
    Activity #3: com.another.app/.AnotherActivity
      Added Fragments:
        #0 com.another.app.ui.AnotherFragment{222222}
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
        frags = parse_fragments_from_dumpsys(FRAGMENTS_SAMPLE, package_hint="com.example.app")
        self.assertEqual(frags, ["HomeFragment", "ChildFragment", "InfoDialogFragment"])

    def test_parse_active_fragments(self):
        frags = parse_fragments_from_dumpsys(FRAGMENTS_ACTIVE_SAMPLE, package_hint="com.example.app")
        self.assertEqual(frags, ["TabFragment", "NestedChildFragment"])

    def test_parse_complex_fragments(self):
        frags = parse_fragments_from_dumpsys(FRAGMENTS_COMPLEX_SAMPLE, package_hint="com.example.app")
        expected = ["HomeFragment", "ChildFragment", "InfoDialogFragment", "NestedChildFragment", "TabFragment"]
        self.assertEqual(frags, expected)

    def test_filter_system_fragments(self):
        frags = parse_fragments_from_dumpsys(FRAGMENTS_ANDROID_SYSTEM_SAMPLE, package_hint="com.example.app")
        # Should only return user-defined fragments, not system ones
        expected = ["HomeFragment", "ChildFragment"]
        self.assertEqual(frags, expected)

    def test_parse_fragments_without_package_hint(self):
        frags = parse_fragments_from_dumpsys(FRAGMENTS_SAMPLE)
        self.assertEqual(frags, ["HomeFragment", "ChildFragment", "InfoDialogFragment"])

    def test_parse_fragments_strict_filtering(self):
        # Test that strict filtering only returns fragments for the specific activity
        frags = parse_fragments_from_dumpsys_strict(
            FULL_DUMPSYS_SAMPLE, 
            "com.example.app/.ui.MainActivity", 
            "com.example.app"
        )
        # Should only return fragments from MainActivity, not from other activities
        self.assertEqual(frags, ["HomeFragment", "ProfileFragment"])


if __name__ == "__main__":
    unittest.main()
