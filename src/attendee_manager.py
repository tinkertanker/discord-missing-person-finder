import os
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

class AttendeeManager:
    """
    Manages attendee information from a CSV file.
    Extracts student names and group information for comparison.
    """
    
    def __init__(self, file_path: Optional[str] = None):
        """
        Initialize the AttendeeManager with an optional file path.
        If no file path is provided, it will try to get it from environment variables.
        
        Args:
            file_path (Optional[str]): Path to the attendee CSV file
        """
        load_dotenv()
        
        self.file_path = file_path or os.getenv('ATTENDEE_LIST_PATH')
        if not self.file_path:
            raise ValueError("No attendee list file path provided. Please set ATTENDEE_LIST_PATH in .env or provide it directly.")
        
        self.attendees = []
        self.groups = {}
        
    def load_attendees(self) -> bool:
        """
        Load attendees from the CSV file.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Attempt to read the CSV file
            df = pd.read_csv(self.file_path)
            
            # Validate that the necessary columns exist
            if len(df.columns) < 12:
                print(f"CSV file does not have enough columns. Found {len(df.columns)}, expected at least 12.")
                return False
            
            # Extract names from column 2 (index 1) and group info from column 12 (index 11)
            name_col = df.iloc[:, 1]
            group_col = df.iloc[:, 11]
            
            # Store attendees with their groups
            for index, name in name_col.items():
                if pd.notna(name) and isinstance(name, str) and name.strip():
                    group = group_col.iloc[index] if pd.notna(group_col.iloc[index]) else "Unassigned"
                    group = str(group).strip()
                    
                    # Add to attendee list
                    self.attendees.append({
                        'name': name.strip(),
                        'group': group
                    })
                    
                    # Update group dictionary
                    if group not in self.groups:
                        self.groups[group] = []
                    self.groups[group].append(name.strip())
            
            print(f"Successfully loaded {len(self.attendees)} attendees from {self.file_path}")
            return True
            
        except Exception as e:
            print(f"Error loading attendees: {str(e)}")
            return False
    
    def get_attendees(self) -> List[Dict[str, str]]:
        """
        Get the list of all attendees.
        
        Returns:
            List[Dict[str, str]]: List of attendee dictionaries with 'name' and 'group' keys
        """
        return self.attendees
    
    def get_attendee_names(self) -> List[str]:
        """
        Get just the names of all attendees.
        
        Returns:
            List[str]: List of attendee names
        """
        return [attendee['name'] for attendee in self.attendees]
    
    def get_groups(self) -> Dict[str, List[str]]:
        """
        Get attendees organized by their groups.
        
        Returns:
            Dict[str, List[str]]: Dictionary with group names as keys and lists of attendee names as values
        """
        return self.groups
    
    def get_attendees_by_group(self, group_name: str) -> List[str]:
        """
        Get all attendees in a specific group.
        
        Args:
            group_name (str): Name of the group
            
        Returns:
            List[str]: List of attendee names in the specified group
        """
        return self.groups.get(group_name, [])

# Example usage
if __name__ == "__main__":
    manager = AttendeeManager()
    if manager.load_attendees():
        print(f"Total attendees: {len(manager.get_attendees())}")
        print(f"Total groups: {len(manager.get_groups())}")
        
        # Print first 5 attendees as example
        print("\nSample attendees:")
        for i, attendee in enumerate(manager.get_attendees()[:5]):
            print(f"{i+1}. {attendee['name']} (Group: {attendee['group']})")