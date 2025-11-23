#!/usr/bin/env python3
"""
Test script to check requirements compatibility before Docker build
"""

import sys
import subprocess
import tempfile
import os

def test_requirements_compatibility():
    """Test if requirements.txt can be installed without conflicts"""

    print("🔍 Testing requirements compatibility...")

    # Read requirements.txt
    with open('requirements.txt', 'r') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    print(f"📦 Found {len(requirements)} requirements:")
    for req in requirements:
        print(f"  - {req}")

    # Test pip install --dry-run
    print("\n🧪 Testing pip dependency resolution...")

    try:
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', '--dry-run', '--quiet'
        ] + requirements, capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            print("✅ All requirements are compatible!")
            return True
        else:
            print("❌ Dependency conflicts found:")
            print(result.stderr)
            return False

    except subprocess.TimeoutExpired:
        print("⏰ Pip resolution timed out (this is normal for complex dependency trees)")
        return None
    except Exception as e:
        print(f"❌ Error testing requirements: {e}")
        return False

def test_mt5linux_import():
    """Test if mt5linux can be imported"""

    print("\n🔧 Testing mt5linux import...")

    try:
        # Try to import mt5linux
        import mt5linux
        print("✅ mt5linux imported successfully")
        print(f"   Version: {getattr(mt5linux, '__version__', 'Unknown')}")

        # Test basic functionality
        if hasattr(mt5linux, 'initialize'):
            print("   ✅ Has initialize method")
        if hasattr(mt5linux, 'login'):
            print("   ✅ Has login method")
        if hasattr(mt5linux, 'shutdown'):
            print("   ✅ Has shutdown method")

        return True

    except ImportError as e:
        print(f"❌ mt5linux import failed: {e}")
        return False
    except Exception as e:
        print(f"⚠️  mt5linux import error: {e}")
        return False

def main():
    print("🚀 MT5 Docker Requirements Test")
    print("=" * 50)

    # Test requirements compatibility
    compat_result = test_requirements_compatibility()

    # Test mt5linux import
    import_result = test_mt5linux_import()

    print("\n" + "=" * 50)
    print("📊 Test Results:")

    if compat_result is True:
        print("✅ Requirements compatibility: PASS")
    elif compat_result is False:
        print("❌ Requirements compatibility: FAIL")
    else:
        print("⏰ Requirements compatibility: TIMEOUT (may still work)")

    if import_result:
        print("✅ mt5linux import: PASS")
    else:
        print("❌ mt5linux import: FAIL")

    if compat_result and import_result:
        print("\n🎉 All tests passed! Ready for Docker build.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check dependency conflicts.")
        return 1

if __name__ == "__main__":
    sys.exit(main())