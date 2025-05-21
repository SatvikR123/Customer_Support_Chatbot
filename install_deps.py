#!/usr/bin/env python3
"""
Helper script to install project dependencies with version pinning.
"""
import subprocess
import sys
import os
import platform

def install_package(package):
    """Install a package using pip with --user flag."""
    try:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", package])
        return True
    except subprocess.CalledProcessError:
        print(f"Failed to install {package}")
        return False

def main():
    # Check if running as root or with sudo (not recommended)
    if os.geteuid() == 0:  # Unix-like systems only
        print("Warning: Running as root is not recommended. Consider using --user flag instead.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Packages to install with version pinning to avoid compatibility issues
    packages = [
        "python-dotenv==1.0.0",
        "beautifulsoup4==4.12.2",
        "requests==2.31.0",
        "numpy==1.24.3",  # Specific version to avoid issues with ChromaDB
        "pandas==2.0.3",
        "chromadb==0.4.18",
        "sentence-transformers==2.2.2",
        "fastapi==0.103.1",
        "uvicorn==0.23.2",
        "websockets==11.0.3",
        "pyautogen==0.2.3",
        "google-generativeai==0.3.2",
        "python-multipart==0.0.6"
    ]
    
    # Install each package
    success_count = 0
    for package in packages:
        if install_package(package):
            success_count += 1
    
    # Print summary
    print(f"\nInstalled {success_count} of {len(packages)} packages.")
    if success_count < len(packages):
        print("Some packages failed to install. Check the output for details.")
    else:
        print("All packages installed successfully!")
        print("\nYou can now run the test script:")
        print("python test_setup.py")

if __name__ == "__main__":
    main() 