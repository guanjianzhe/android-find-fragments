#!/usr/bin/env python3
"""
Multi-device testing script for ACF tool across different Android versions.
"""

import os
import sys
import time
from typing import Dict, List, Optional, Tuple

# Handle imports for both direct execution and module execution
try:
    # Try relative imports first (when run as module)
    from ..adb_client import get_android_version, get_connected_devices, get_activities_dump, get_current_activity_fast
    from ..file_finder import get_activity_name
    from ..fragment_finder import find_fragments_for_activity, find_fragments_for_activity_optimized
    from ..parsers import parse_activity_component
except ImportError:
    # Fall back to absolute imports (when run directly)
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from tools.adb_client import get_android_version, get_connected_devices, get_activities_dump, get_current_activity_fast
    from tools.file_finder import get_activity_name
    from tools.fragment_finder import find_fragments_for_activity, find_fragments_for_activity_optimized
    from tools.parsers import parse_activity_component


class DeviceTestResult:
    """Test result for a single device."""
    
    def __init__(self, device_id: str, android_version: Optional[int]):
        self.device_id = device_id
        self.android_version = android_version
        self.tests: List[Dict] = []
        self.success_count = 0
        self.total_count = 0
    
    def add_test(self, test_name: str, success: bool, details: str = ""):
        """Add a test result."""
        self.tests.append({
            "name": test_name,
            "success": success,
            "details": details
        })
        self.total_count += 1
        if success:
            self.success_count += 1
    
    def get_summary(self) -> str:
        """Get test summary."""
        return f"Device {self.device_id} (Android {self.android_version}): {self.success_count}/{self.total_count} tests passed"


def test_device_connection(device_id: str) -> Tuple[bool, str]:
    """Test basic device connection."""
    try:
        # Import at function level to ensure proper loading
        try:
            from ..adb_client import run_command, build_adb_command
        except ImportError:
            from tools.adb_client import run_command, build_adb_command
        result = run_command(build_adb_command("adb", device_id, ["shell", "echo", "test"]))
        if "test" in result:
            return True, "Device connection successful"
        else:
            return False, f"Unexpected response: {result}"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"


def test_android_version_detection(device_id: str) -> Tuple[bool, str, Optional[int]]:
    """Test Android version detection."""
    try:
        version = get_android_version("adb", device_id)
        if version is not None:
            return True, f"Android version detected: {version}", version
        else:
            return False, "Failed to detect Android version", None
    except Exception as e:
        return False, f"Version detection failed: {str(e)}", None


def test_activity_parsing(device_id: str, android_version: int) -> Tuple[bool, str]:
    """Test activity parsing for the device."""
    try:
        activities_dump = get_activities_dump("adb", device_id)
        activity_component = parse_activity_component(activities_dump, prefer_top=(android_version >= 12))
        activity_name = get_activity_name(activity_component)
        
        # Check if we got a valid activity
        if activity_name and "." in activity_component:
            return True, f"Activity parsed: {activity_name} ({activity_component})"
        else:
            return False, f"Invalid activity parsed: {activity_component}"
    except Exception as e:
        return False, f"Activity parsing failed: {str(e)}"


def test_fragment_parsing(device_id: str, android_version: int) -> Tuple[bool, str]:
    """Test fragment parsing for the device."""
    try:
        activities_dump = get_activities_dump("adb", device_id)
        activity_component = parse_activity_component(activities_dump, prefer_top=(android_version >= 12))
        fragments = find_fragments_for_activity("adb", device_id, activity_component)
        
        # Check if parsing completed without errors
        if isinstance(fragments, list):
            fragment_count = len(fragments)
            return True, f"Fragment parsing successful: {fragment_count} fragments found"
        else:
            return False, f"Fragment parsing returned invalid result: {type(fragments)}"
    except Exception as e:
        return False, f"Fragment parsing failed: {str(e)}"


def test_optimized_parsing(device_id: str, android_version: int) -> Tuple[bool, str]:
    """Test optimized parsing functionality (fast activity lookup + package-specific dumpsys)."""
    try:
        # Test fast activity lookup
        activity_component = get_current_activity_fast("adb", device_id, android_version)
        
        if not activity_component:
            return False, "Fast activity lookup failed"
        
        # Test optimized fragment parsing
        fragments = find_fragments_for_activity_optimized("adb", device_id, activity_component)
        
        return True, f"Optimized parsing successful: {len(fragments)} fragments found"
    except Exception as e:
        return False, f"Optimized parsing failed: {str(e)}"


def test_dumpsys_format_compatibility(device_id: str, android_version: int) -> Tuple[bool, str]:
    """Test dumpsys format compatibility."""
    try:
        activities_dump = get_activities_dump("adb", device_id)
        
        # Check for expected keys based on Android version
        if android_version >= 12:
            expected_key = "topResumedActivity"
        else:
            expected_key = "mResumedActivity"
        
        if expected_key in activities_dump:
            return True, f"Found expected key '{expected_key}' in dumpsys output"
        else:
            # Check if the other key exists (fallback)
            fallback_key = "mResumedActivity" if expected_key == "topResumedActivity" else "topResumedActivity"
            if fallback_key in activities_dump:
                return True, f"Found fallback key '{fallback_key}' instead of '{expected_key}'"
            else:
                return False, f"Neither '{expected_key}' nor '{fallback_key}' found in dumpsys output"
    except Exception as e:
        return False, f"Dumpsys format test failed: {str(e)}"


def run_device_tests(device_id: str) -> DeviceTestResult:
    """Run all tests for a single device."""
    print(f"\n=== Testing Device: {device_id} ===")
    
    result = DeviceTestResult(device_id, None)
    
    # Test 1: Device connection
    success, details = test_device_connection(device_id)
    result.add_test("Device Connection", success, details)
    if not success:
        print(f"❌ Device connection failed: {details}")
        return result
    
    # Test 2: Android version detection
    success, details, version = test_android_version_detection(device_id)
    result.add_test("Android Version Detection", success, details)
    result.android_version = version
    if not success:
        print(f"❌ Version detection failed: {details}")
        return result
    
    print(f"✅ Android {version} detected")
    
    # Test 3: Dumpsys format compatibility
    success, details = test_dumpsys_format_compatibility(device_id, version)
    result.add_test("Dumpsys Format Compatibility", success, details)
    if not success:
        print(f"❌ Dumpsys format incompatible: {details}")
    
    # Test 4: Activity parsing
    success, details = test_activity_parsing(device_id, version)
    result.add_test("Activity Parsing", success, details)
    if not success:
        print(f"❌ Activity parsing failed: {details}")
    else:
        print(f"✅ {details}")
    
    # Test 5: Fragment parsing
    success, details = test_fragment_parsing(device_id, version)
    result.add_test("Fragment Parsing", success, details)
    if not success:
        print(f"❌ Fragment parsing failed: {details}")
    else:
        print(f"✅ {details}")
    
    # Test 6: Optimized parsing
    success, details = test_optimized_parsing(device_id, version)
    result.add_test("Optimized Parsing", success, details)
    if not success:
        print(f"❌ Optimized parsing failed: {details}")
    else:
        print(f"✅ {details}")
    
    return result


def run_multi_device_tests() -> List[DeviceTestResult]:
    """Run tests on all connected devices."""
    print("=== ACF Multi-Device Compatibility Test ===")
    
    # Get all connected devices
    try:
        devices = get_connected_devices("adb")
        if not devices:
            print("❌ No devices connected")
            return []
        
        print(f"Found {len(devices)} connected device(s): {', '.join(devices)}")
        
        results = []
        for device_id in devices:
            result = run_device_tests(device_id)
            results.append(result)
            time.sleep(1)  # Brief pause between devices
        
        return results
        
    except Exception as e:
        print(f"❌ Failed to get device list: {str(e)}")
        return []


def print_test_report(results: List[DeviceTestResult]):
    """Print comprehensive test report."""
    print("\n" + "="*60)
    print("TEST REPORT")
    print("="*60)
    
    total_devices = len(results)
    successful_devices = sum(1 for r in results if r.success_count == r.total_count)
    
    print(f"Total devices tested: {total_devices}")
    print(f"Fully successful devices: {successful_devices}")
    print(f"Success rate: {successful_devices/total_devices*100:.1f}%" if total_devices > 0 else "N/A")
    
    print("\nDetailed Results:")
    for result in results:
        print(f"\n{result.get_summary()}")
        for test in result.tests:
            status = "✅" if test["success"] else "❌"
            print(f"  {status} {test['name']}: {test['details']}")
    
    # Version compatibility summary
    print("\nVersion Compatibility Summary:")
    version_stats = {}
    for result in results:
        if result.android_version:
            version = result.android_version
            if version not in version_stats:
                version_stats[version] = {"total": 0, "successful": 0}
            version_stats[version]["total"] += 1
            if result.success_count == result.total_count:
                version_stats[version]["successful"] += 1
    
    for version in sorted(version_stats.keys()):
        stats = version_stats[version]
        success_rate = stats["successful"] / stats["total"] * 100
        print(f"  Android {version}: {stats['successful']}/{stats['total']} devices ({success_rate:.1f}%)")


def main():
    """Main entry point for multi-device testing."""
    try:
        results = run_multi_device_tests()
        if results:
            print_test_report(results)
            
            # Exit with error code if any device failed
            failed_devices = [r for r in results if r.success_count != r.total_count]
            if failed_devices:
                print(f"\n⚠️  {len(failed_devices)} device(s) had test failures")
                sys.exit(1)
            else:
                print("\n🎉 All devices passed all tests!")
                sys.exit(0)
        else:
            print("❌ No devices were tested")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Testing failed with error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
