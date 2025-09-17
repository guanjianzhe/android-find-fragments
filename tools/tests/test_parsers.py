"""Tests for ACF parsers."""

import unittest

from tools.parsers import parse_activity_component, parse_fragments, parse_fragments_strict
from tools.test_data import (
    ANDROID11_SAMPLE,
    ANDROID14_SAMPLE,
    FRAGMENTS_ACTIVE_SAMPLE,
    FRAGMENTS_ANDROID_SYSTEM_SAMPLE,
    FRAGMENTS_COMPLEX_SAMPLE,
    FRAGMENTS_SAMPLE,
    FULL_DUMPSYS_SAMPLE,
)


class TestParsers(unittest.TestCase):
    """Test cases for parser functions."""

    def test_parse_activity_11(self):
        """Test parsing Android 11 activity."""
        comp = parse_activity_component(ANDROID11_SAMPLE, prefer_top=False)
        self.assertEqual(comp, "com.example.app/.ui.MainActivity")

    def test_parse_activity_14(self):
        """Test parsing Android 14 activity."""
        comp = parse_activity_component(ANDROID14_SAMPLE, prefer_top=True)
        self.assertEqual(comp, "com.example.app/.ui.MainActivity")

    def test_parse_fragments(self):
        """Test parsing fragments from Added Fragments section."""
        frags = parse_fragments(FRAGMENTS_SAMPLE, package_hint="com.example.app")
        self.assertEqual(frags, ["HomeFragment", "ChildFragment", "InfoDialogFragment"])

    def test_parse_active_fragments(self):
        """Test parsing fragments from Active Fragments section."""
        frags = parse_fragments(FRAGMENTS_ACTIVE_SAMPLE, package_hint="com.example.app")
        self.assertEqual(frags, ["TabFragment", "NestedChildFragment"])

    def test_parse_complex_fragments(self):
        """Test parsing complex fragment scenarios."""
        frags = parse_fragments(FRAGMENTS_COMPLEX_SAMPLE, package_hint="com.example.app")
        expected = ["HomeFragment", "ChildFragment", "InfoDialogFragment", "NestedChildFragment", "TabFragment"]
        self.assertEqual(frags, expected)

    def test_filter_system_fragments(self):
        """Test filtering out system fragments."""
        frags = parse_fragments(FRAGMENTS_ANDROID_SYSTEM_SAMPLE, package_hint="com.example.app")
        # Should only return user-defined fragments, not system ones
        expected = ["HomeFragment", "ChildFragment"]
        self.assertEqual(frags, expected)

    def test_parse_fragments_without_package_hint(self):
        """Test parsing fragments without package hint."""
        frags = parse_fragments(FRAGMENTS_SAMPLE)
        self.assertEqual(frags, ["HomeFragment", "ChildFragment", "InfoDialogFragment"])

    def test_parse_fragments_strict_filtering(self):
        """Test that strict filtering only returns fragments for the specific activity."""
        frags = parse_fragments_strict(
            FULL_DUMPSYS_SAMPLE, 
            "com.example.app/.ui.MainActivity", 
            "com.example.app"
        )
        # Should only return fragments from MainActivity, not from other activities
        self.assertEqual(frags, ["HomeFragment", "ProfileFragment"])


if __name__ == "__main__":
    unittest.main()