import unittest
import tempfile
import pandas as pd
import os
from src.attendee_manager import AttendeeManager
from src.name_matcher import NameMatcher

class TestIntegration(unittest.TestCase):
    """Integration tests for the attendance checker functionality."""
    
    def setUp(self):
        # Create a temporary CSV file for testing
        self.temp_csv = tempfile.NamedTemporaryFile(suffix='.csv', delete=False)
        
        # Create sample data
        data = {
            'Column1': list(range(1, 11)),
            'Name': [
                'John Doe', 
                'Jane Smith', 
                'Bob Johnson', 
                'Alice Brown',
                'Michael Williams',
                'Sarah Jones',
                'David Miller',
                'Emily Davis',
                'James Wilson',
                'Emma Taylor'
            ],
            'Column3': ['A'] * 10,
            'Column4': ['B'] * 10,
            'Column5': ['C'] * 10,
            'Column6': ['D'] * 10,
            'Column7': ['E'] * 10,
            'Column8': ['F'] * 10,
            'Column9': ['G'] * 10,
            'Column10': ['H'] * 10,
            'Column11': ['I'] * 10,
            'Group': [
                'Team Alpha',
                'Team Alpha',
                'Team Beta',
                'Team Beta',
                'Team Gamma',
                'Team Gamma',
                'Team Delta',
                'Team Delta',
                'Team Epsilon',
                'Team Epsilon'
            ]
        }
        
        df = pd.DataFrame(data)
        df.to_csv(self.temp_csv.name, index=False)
        
        # Sample Discord usernames (some match, some don't)
        self.discord_names = [
            'john_doe',              # Match for John Doe
            'jane.smith',            # Match for Jane Smith
            'bobby.j',               # Match for Bob Johnson
            'mwilliams',             # Match for Michael Williams
            'sarah123',              # Match for Sarah Jones
            'dave_miller',           # Match for David Miller
            'random_user1',          # No match
            'random_user2',          # No match
            'james.wilson',          # Match for James Wilson
            'bot_user'               # No match
        ]
        
        # Save the path for use in tests
        self.csv_path = self.temp_csv.name
    
    def tearDown(self):
        # Clean up the temporary file
        os.unlink(self.temp_csv.name)
    
    def test_end_to_end_workflow(self):
        """Test the entire workflow from CSV loading to missing attendee identification."""
        
        # 1. Load attendees from CSV
        manager = AttendeeManager(self.csv_path)
        self.assertTrue(manager.load_attendees())
        
        attendees = manager.get_attendees()
        attendee_names = manager.get_attendee_names()
        groups = manager.get_groups()
        
        # Verify data was loaded correctly
        self.assertEqual(len(attendees), 10)
        self.assertEqual(len(groups), 5)
        
        # 2. Create name matcher
        matcher = NameMatcher(similarity_threshold=80)
        
        # 3. Find missing attendees
        missing_names = matcher.find_missing_attendees(self.discord_names, attendee_names)
        
        # 4. Verify results
        expected_missing = ['Alice Brown', 'Emily Davis', 'Emma Taylor']
        self.assertEqual(sorted(missing_names), sorted(expected_missing))
        
        # 5. Structure missing attendees by group
        missing_by_group = {}
        for name in missing_names:
            group = next((a['group'] for a in attendees if a['name'] == name), "Unknown")
            if group not in missing_by_group:
                missing_by_group[group] = []
            missing_by_group[group].append(name)
        
        # 6. Verify grouping
        self.assertEqual(len(missing_by_group), 3)
        self.assertEqual(set(missing_by_group.keys()), set(['Team Beta', 'Team Delta', 'Team Epsilon']))
        self.assertEqual(missing_by_group['Team Beta'], ['Alice Brown'])
        self.assertEqual(missing_by_group['Team Delta'], ['Emily Davis'])
        self.assertEqual(missing_by_group['Team Epsilon'], ['Emma Taylor'])
    
    def test_with_different_threshold(self):
        """Test how changing the matching threshold affects results."""
        
        # Load attendees
        manager = AttendeeManager(self.csv_path)
        manager.load_attendees()
        attendee_names = manager.get_attendee_names()
        
        # Test with stricter threshold (90)
        strict_matcher = NameMatcher(similarity_threshold=90)
        strict_missing = strict_matcher.find_missing_attendees(self.discord_names, attendee_names)
        
        # Test with more lenient threshold (70)
        lenient_matcher = NameMatcher(similarity_threshold=70)
        lenient_missing = lenient_matcher.find_missing_attendees(self.discord_names, attendee_names)
        
        # Stricter threshold should result in more missing attendees
        self.assertGreater(len(strict_missing), len(lenient_missing))

if __name__ == '__main__':
    unittest.main()