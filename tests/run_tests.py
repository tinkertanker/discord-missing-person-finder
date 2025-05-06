#!/usr/bin/env python3
import unittest
import sys
import os

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import test modules
from tests.test_name_matcher import TestNameMatcher
from tests.test_attendee_manager import TestAttendeeManager
from tests.test_integration import TestIntegration

def run_tests():
    # Create a test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add tests to the suite
    suite.addTests(loader.loadTestsFromTestCase(TestNameMatcher))
    suite.addTests(loader.loadTestsFromTestCase(TestAttendeeManager))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return appropriate exit code
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    sys.exit(run_tests())