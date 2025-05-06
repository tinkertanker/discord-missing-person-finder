import unittest
from src.name_matcher import NameMatcher

class TestNameMatcher(unittest.TestCase):
    
    def setUp(self):
        # Create a NameMatcher instance with a threshold of 80
        self.matcher = NameMatcher(similarity_threshold=80)
        
    def test_normalize_name(self):
        # Test name normalization
        test_cases = [
            ("John Doe", "john doe"),
            ("john.doe", "john doe"),
            ("john_doe", "john doe"),
            ("JohnDoe#1234", "johndoe"),
            ("John-Doe", "john doe"),
            ("   John   Doe   ", "john doe"),
            ("John(Doe)", "john doe"),
        ]
        
        for input_name, expected_output in test_cases:
            with self.subTest(input_name=input_name):
                self.assertEqual(self.matcher.normalize_name(input_name), expected_output)
    
    def test_exact_match(self):
        # Test exact matches
        self.assertTrue(self.matcher.is_match("John Doe", "John Doe")[0])
        self.assertTrue(self.matcher.is_match("john_doe", "John Doe")[0])
        self.assertTrue(self.matcher.is_match("JohnDoe#1234", "John Doe")[0])
        
    def test_close_match(self):
        # Test close matches that should be above threshold
        self.assertTrue(self.matcher.is_match("Johnny Doe", "John Doe")[0])
        self.assertTrue(self.matcher.is_match("Jhn Doe", "John Doe")[0]) 
        self.assertTrue(self.matcher.is_match("john.doey", "John Doe")[0])
    
    def test_non_match(self):
        # Test non-matches that should be below threshold
        self.assertFalse(self.matcher.is_match("Alice Smith", "John Doe")[0])
        self.assertFalse(self.matcher.is_match("Bob Johnson", "John Doe")[0])
        
    def test_threshold_effect(self):
        # Test that changing the threshold affects matching
        strict_matcher = NameMatcher(similarity_threshold=90)
        lenient_matcher = NameMatcher(similarity_threshold=60)
        
        # This match should pass with lenient threshold but fail with strict
        test_name = "Jon Do"  # Slightly different from "John Doe"
        self.assertFalse(strict_matcher.is_match(test_name, "John Doe")[0])
        self.assertTrue(lenient_matcher.is_match(test_name, "John Doe")[0])
    
    def test_find_best_match(self):
        # Test finding best match from a list
        attendee_names = ["John Doe", "Jane Smith", "Bob Johnson", "Alice Brown"]
        
        best_match, score = self.matcher.find_best_match("john_doe", attendee_names)
        self.assertEqual(best_match, "John Doe")
        self.assertGreaterEqual(score, 80)
        
        best_match, score = self.matcher.find_best_match("alice.b", attendee_names)
        self.assertEqual(best_match, "Alice Brown")
        self.assertGreaterEqual(score, 80)
        
        best_match, score = self.matcher.find_best_match("unknown_person", attendee_names)
        self.assertIsNone(best_match)
        self.assertLess(score, 80)
    
    def test_find_missing_attendees(self):
        # Test finding missing attendees
        discord_users = ["john_doe", "jane.smith", "bob123"]
        attendee_names = ["John Doe", "Jane Smith", "Bob Johnson", "Alice Brown"]
        
        missing = self.matcher.find_missing_attendees(discord_users, attendee_names)
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0], "Alice Brown")
        
        # Test with all attendees present
        discord_users = ["john_doe", "jane.smith", "bob_johnson", "alice.brown"]
        missing = self.matcher.find_missing_attendees(discord_users, attendee_names)
        self.assertEqual(len(missing), 0)
        
        # Test with no attendees in Discord
        discord_users = ["unknown1", "unknown2"]
        missing = self.matcher.find_missing_attendees(discord_users, attendee_names)
        self.assertEqual(len(missing), 4)
        self.assertEqual(set(missing), set(attendee_names))

if __name__ == "__main__":
    unittest.main()