#!/usr/bin/env python3
"""Urmom Lang - Main Entry Point"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.cli import main

if __name__ == '__main__':
    sys.exit(main() or 0)
