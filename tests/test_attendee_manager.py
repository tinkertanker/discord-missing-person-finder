import unittest
import os
import tempfile
import pandas as pd
from src.attendee_manager import AttendeeManager

class TestAttendeeManager(unittest.TestCase):
    
    def setUp(self):
        # Create a temporary CSV file for testing
        self.temp_csv = tempfile.NamedTemporaryFile(suffix='.csv', delete=False)
        
        # Create sample data
        data = {
            'Column1': [1, 2, 3, 4],
            'Name': ['John Doe', 'Jane Smith', 'Bob Johnson', 'Alice Brown'],
            'Column3': ['A', 'B', 'C', 'D'],
            'Column4': ['X', 'Y', 'Z', 'W'],
            'Column5': [10, 20, 30, 40],
            'Column6': ['AA', 'BB', 'CC', 'DD'],
            'Column7': [100, 200, 300, 400],
            'Column8': ['XX', 'YY', 'ZZ', 'WW'],
            'Column9': [1000, 2000, 3000, 4000],
            'Column10': ['AAA', 'BBB', 'CCC', 'DDD'],
            'Column11': [5, 6, 7, 8],
            'Group': ['Team A', 'Team A', 'Team B', 'Team B']
        }
        
        df = pd.DataFrame(data)
        df.to_csv(self.temp_csv.name, index=False)
        
        # Save the path for use in tests
        self.csv_path = self.temp_csv.name
        
        # Set the environment variable for testing
        os.environ['ATTENDEE_LIST_PATH'] = self.csv_path
    
    def tearDown(self):
        # Clean up the temporary file
        os.unlink(self.temp_csv.name)
        
        # Clean up environment variable
        if 'ATTENDEE_LIST_PATH' in os.environ:
            del os.environ['ATTENDEE_LIST_PATH']
    
    def test_init_with_path(self):
        # Test initialization with a direct path
        manager = AttendeeManager(self.csv_path)
        self.assertEqual(manager.file_path, self.csv_path)
    
    def test_init_with_env_var(self):
        # Test initialization with an environment variable
        manager = AttendeeManager()
        self.assertEqual(manager.file_path, self.csv_path)
    
    def test_load_attendees(self):
        # Test loading attendees from the CSV
        manager = AttendeeManager(self.csv_path)
        self.assertTrue(manager.load_attendees())
        
        # Check that the correct number of attendees were loaded
        self.assertEqual(len(manager.get_attendees()), 4)
        
        # Check that the names and groups were extracted correctly
        attendees = manager.get_attendees()
        self.assertEqual(attendees[0]['name'], 'John Doe')
        self.assertEqual(attendees[0]['group'], 'Team A')
        self.assertEqual(attendees[1]['name'], 'Jane Smith')
        self.assertEqual(attendees[1]['group'], 'Team A')
        self.assertEqual(attendees[2]['name'], 'Bob Johnson')
        self.assertEqual(attendees[2]['group'], 'Team B')
        self.assertEqual(attendees[3]['name'], 'Alice Brown')
        self.assertEqual(attendees[3]['group'], 'Team B')
    
    def test_get_attendee_names(self):
        # Test getting just the attendee names
        manager = AttendeeManager(self.csv_path)
        manager.load_attendees()
        
        names = manager.get_attendee_names()
        self.assertEqual(len(names), 4)
        self.assertEqual(set(names), {'John Doe', 'Jane Smith', 'Bob Johnson', 'Alice Brown'})
    
    def test_get_groups(self):
        # Test getting attendees organized by groups
        manager = AttendeeManager(self.csv_path)
        manager.load_attendees()
        
        groups = manager.get_groups()
        self.assertEqual(len(groups), 2)
        self.assertIn('Team A', groups)
        self.assertIn('Team B', groups)
        self.assertEqual(set(groups['Team A']), {'John Doe', 'Jane Smith'})
        self.assertEqual(set(groups['Team B']), {'Bob Johnson', 'Alice Brown'})
    
    def test_get_attendees_by_group(self):
        # Test getting attendees for a specific group
        manager = AttendeeManager(self.csv_path)
        manager.load_attendees()
        
        team_a = manager.get_attendees_by_group('Team A')
        self.assertEqual(len(team_a), 2)
        self.assertEqual(set(team_a), {'John Doe', 'Jane Smith'})
        
        team_b = manager.get_attendees_by_group('Team B')
        self.assertEqual(len(team_b), 2)
        self.assertEqual(set(team_b), {'Bob Johnson', 'Alice Brown'})
        
        # Test getting attendees for a non-existent group
        unknown_team = manager.get_attendees_by_group('Unknown Team')
        self.assertEqual(len(unknown_team), 0)
    
    def test_invalid_file_path(self):
        # Test behavior with an invalid file path
        manager = AttendeeManager('/nonexistent/path.csv')
        self.assertFalse(manager.load_attendees())
        self.assertEqual(len(manager.get_attendees()), 0)

if __name__ == '__main__':
    unittest.main()