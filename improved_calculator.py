#!/usr/bin/env python3
"""
Irish Capital Gains Calculator - Main Entry Point

Run from project root: python improved_calculator.py [files] [options]
"""

import sys
import os

# Add src directory to path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the calculator
from improved_calculator import main

if __name__ == "__main__":
    main()
