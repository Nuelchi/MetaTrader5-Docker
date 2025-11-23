#!/usr/bin/env python3
"""
Test script to verify requirements installation before Docker build
"""

import sys
import subprocess
import os

def run_command(cmd, description):
    """Run a command and return success/failure"""
    print(f"\n🔍 Testing: {description}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            print(f"✅ SUCCESS: {description}")
            return True
        else:
            print(f"❌ FAILED: {description}")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ ERROR: {description} - {e}")
        return False

def test_package_availability():
    """Test if packages can be installed"""
    print("🚀 Testing package installation...")

    # Test basic packages first
    basic_packages = [
        "fastapi==0.104.1",
        "uvicorn==0.24.0",
        "websockets==12.0",
        "pydantic==2.5.0"
    ]

    for package in basic_packages:
        if not run_command(f"pip install --dry-run {package}", f"Check {package} availability"):
            return False

    # Test MetaTrader5 separately (known to be problematic)
    print("\n🔍 Testing MetaTrader5 installation...")
    try:
        # Try to find MetaTrader5 wheel
        result = subprocess.run("pip index versions MetaTrader5", shell=True, capture_output=True, text=True)
        if "MetaTrader5" in result.stdout:
            print("✅ MetaTrader5 found in PyPI index")
            return run_command("pip install --dry-run MetaTrader5==5.0.36", "MetaTrader5 5.0.36 availability")
        else:
            print("❌ MetaTrader5 not found in PyPI index")
            print("💡 MetaTrader5 needs to be installed from a wheel file or alternative source")
            return False
    except Exception as e:
        print(f"❌ Error checking MetaTrader5: {e}")
        return False

def test_mt5linux_alternative():
    """Test mt5linux as alternative"""
    print("\n🔍 Testing mt5linux alternative...")
    return run_command("pip install --dry-run mt5linux==0.1.9", "mt5linux 0.1.9 availability")

def main():
    print("🧪 MT5 Server Requirements Test")
    print("=" * 50)

    # Change to the correct directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    success = True

    # Test package availability
    if not test_package_availability():
        success = False

    # Test alternative
    if not test_mt5linux_alternative():
        print("⚠️  mt5linux alternative also failed")

    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed! Ready for Docker build.")
        return 0
    else:
        print("❌ Some tests failed. Need to fix requirements.")
        print("\n💡 Solutions:")
        print("1. Remove MetaTrader5==5.0.36 from requirements.txt")
        print("2. Use mt5linux==0.1.9 instead")
        print("3. Or install MetaTrader5 from a wheel file")
        return 1

if __name__ == "__main__":
    sys.exit(main())