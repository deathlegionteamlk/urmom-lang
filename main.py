#!/usr/bin/env python3
"""
Urmom Lang - Main Entry Point
A modern, simple, concurrent programming language by Death Legion Team.
"""

import sys
import os

# Ensure the package is findable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.cli import main

if __name__ == '__main__':
    main()
