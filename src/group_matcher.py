import re
import csv
import pandas as pd
from typing import Dict, List, Tuple, Optional, Set, Any
from fuzzywuzzy import fuzz, process
from datetime import datetime

class GroupMatcher:
    """
    Match attendees to Discord members using group information and name similarity.
    This class leverages the cat-x-grp-y Discord roles to improve matching accuracy.
    """
    
    def __init__(self, similarity_threshold: int = 70, debug: bool = False):
        """
        Initialize the GroupMatcher.
        
        Args:
            similarity_threshold (int): Threshold for name similarity (0-100)
            debug (bool): Whether to print debug information
        """
        self.threshold = similarity_threshold
        self.debug = debug
        self.debug_file = None
    
    def set_debug(self, debug: bool, debug_file: Optional[str] = None):
        """Set debug mode and optionally specify a debug file."""
        self.debug = debug
        self.debug_file = debug_file
        
        if debug and debug_file:
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(f"Group Matcher Debug Log - {datetime.now()}\n")
                f.write(f"Similarity threshold: {self.threshold}\n")
                f.write("-" * 80 + "\n\n")
    
    def _debug_print(self, message: str):
        """Print debug message if debug mode is enabled."""
        if self.debug:
            print(message)
            if self.debug_file:
                with open(self.debug_file, 'a', encoding='utf-8') as f:
                    f.write(message + "\n")
    
    def normalize_name(self, name: str) -> str:
        """
        Normalize a name for better comparison.
        
        Args:
            name (str): Name to normalize
            
        Returns:
            str: Normalized name
        """
        if not name:
            return ""
        
        # Extract name after slash if present
        if '/' in name:
            parts = name.split('/')
            if len(parts) > 1 and len(parts[1].strip()) > 0:
                name = parts[1].strip()
        
        # Convert to lowercase
        normalized = name.lower()
        
        # Remove Discord discriminators
        if '#' in normalized:
            normalized = normalized.split('#')[0]
        
        # Remove special characters
        for char in ['.', ',', '-', '_', '(', ')', '[', ']', '{', '}', ':', ';']:
            normalized = normalized.replace(char, ' ')
        
        # Trim and remove consecutive spaces
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def extract_group_code(self, column_value: str) -> str:
        """
        Extract group code (cat-x-grp-y) from a string or return empty string.
        
        Args:
            column_value (str): Text to search for group code
            
        Returns:
            str: Group code if found, otherwise empty string
        """
        # Direct match for cat-x-grp-y format
        if isinstance(column_value, str):
            match = re.search(r'(cat-\d+-grp-\d+)', column_value)
            if match:
                return match.group(1)
        
        return ""
    
    def load_discord_members(self, filepath: str) -> Dict[str, Dict[str, Any]]:
        """
        Load Discord members from the exported file.
        
        Args:
            filepath (str): Path to the exported Discord members file
            
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of Discord members with their details
        """
        discord_members = {}
        group_members = {}  # Members organized by group
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split('|')
                    if len(parts) >= 5:  # ID|DisplayName|Username|Nickname|Group|Roles
                        discord_id = parts[0]
                        display_name = parts[1]
                        username = parts[2]
                        nickname = parts[3] if len(parts) > 3 and parts[3] else ""
                        group_code = parts[4] if len(parts) > 4 and parts[4] else ""
                        
                        # Store member details
                        discord_members[discord_id] = {
                            'id': discord_id,
                            'display_name': display_name,
                            'username': username,
                            'nickname': nickname,
                            'group_code': group_code,
                            'normalized_name': self.normalize_name(display_name)
                        }
                        
                        # Organize by group
                        if group_code:
                            if group_code not in group_members:
                                group_members[group_code] = []
                            group_members[group_code].append(discord_id)
            
            if self.debug:
                self._debug_print(f"Loaded {len(discord_members)} Discord members from {filepath}")
                self._debug_print(f"Found {len(group_members)} distinct groups")
                
            return discord_members, group_members
        
        except Exception as e:
            if self.debug:
                self._debug_print(f"Error loading Discord members: {str(e)}")
            return {}, {}
    
    def load_attendees(self, filepath: str) -> Dict[str, Dict[str, Any]]:
        """
        Load attendees from CSV file.
        
        Args:
            filepath (str): Path to the attendees CSV file
            
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of attendees with their details
        """
        attendees = {}
        group_attendees = {}  # Attendees organized by group
        
        try:
            # Read the CSV file
            df = pd.read_csv(filepath)
            
            # Get the column names to find the right columns
            col_names = df.columns.tolist()
            
            # Find the relevant columns
            # Assume ID is in the first column (index 0)
            id_col = df.iloc[:, 0] if len(df.columns) > 0 else None
            
            # Assume name is in the second column (index 1)
            name_col = df.iloc[:, 1] if len(df.columns) > 1 else None
            
            # Assume email is in the third column (index 2)
            email_col = df.iloc[:, 2] if len(df.columns) > 2 else None
            
            # Assume phone is in the fourth column (index 3)
            phone_col = df.iloc[:, 3] if len(df.columns) > 3 else None
            
            # Assume group is in column 12 (index 11)
            group_col = df.iloc[:, 11] if len(df.columns) > 11 else None
            
            if name_col is None:
                if self.debug:
                    self._debug_print("Error: Could not find name column in CSV")
                return {}, {}
            
            # Process each attendee
            for i, name in name_col.items():
                if pd.notna(name) and isinstance(name, str) and name.strip():
                    # Extract attendee information
                    attendee_record_id = str(id_col.iloc[i]) if id_col is not None and pd.notna(id_col.iloc[i]) else ""
                    email = str(email_col.iloc[i]) if email_col is not None and pd.notna(email_col.iloc[i]) else ""
                    phone = str(phone_col.iloc[i]) if phone_col is not None and pd.notna(phone_col.iloc[i]) else ""
                    group = ""
                    if group_col is not None and i < len(group_col):
                        if pd.notna(group_col.iloc[i]):
                            group = str(group_col.iloc[i]).strip()
                    
                    # Create a clean unique ID for the attendee
                    attendee_id = f"a{i}"
                    normalized_name = self.normalize_name(name)
                    
                    # Store attendee details
                    attendees[attendee_id] = {
                        'attendee_id': attendee_id,
                        'id': attendee_record_id,
                        'name': name.strip(),
                        'email': email,
                        'phone': phone,
                        'group': group,
                        'normalized_name': normalized_name,
                        'row_index': i
                    }
                    
                    # Organize by group
                    if group:
                        if group not in group_attendees:
                            group_attendees[group] = []
                        group_attendees[group].append(attendee_id)
            
            if self.debug:
                self._debug_print(f"Loaded {len(attendees)} attendees from {filepath}")
                self._debug_print(f"Found {len(group_attendees)} distinct groups")
            
            return attendees, group_attendees
        
        except Exception as e:
            if self.debug:
                self._debug_print(f"Error loading attendees: {str(e)}")
            return {}, {}
    
    def map_groups(self, discord_groups: Dict[str, List[str]], 
                 attendee_groups: Dict[str, List[str]]) -> Dict[str, str]:
        """
        Map Discord groups (cat-x-grp-y) to attendee groups.
        
        Args:
            discord_groups: Dictionary of Discord members organized by group code
            attendee_groups: Dictionary of attendees organized by group
            
        Returns:
            Dict[str, str]: Mapping from Discord group codes to attendee group names
        """
        group_mapping = {}
        
        # Find the likely match for each Discord group
        for discord_group, members in discord_groups.items():
            best_match = None
            best_score = 0
            
            # Extract the group number from cat-x-grp-y format
            group_match = re.search(r'cat-(\d+)-grp-(\d+)', discord_group)
            if group_match:
                category_num = group_match.group(1)
                group_num = group_match.group(2)
                
                # Look for similar patterns in attendee groups
                for attendee_group in attendee_groups.keys():
                    # Check for exact or partial matches
                    attendee_group_lower = attendee_group.lower()
                    
                    # Check for common patterns:
                    # 1. Exact "cat-x-grp-y" in attendee group
                    if discord_group.lower() in attendee_group_lower:
                        score = 100
                    # 2. Just the "grp-y" part 
                    elif f"grp-{group_num}" in attendee_group_lower:
                        score = 90
                    # 3. Just the number
                    elif f"group {group_num}" in attendee_group_lower or f"team {group_num}" in attendee_group_lower:
                        score = 85
                    # 4. Group number at the end
                    elif attendee_group_lower.endswith(f" {group_num}"):
                        score = 80
                    # 5. Fall back to if the numbers match somewhere
                    elif group_num in attendee_group_lower:
                        score = 70
                    else:
                        score = 0
                    
                    if score > best_score:
                        best_score = score
                        best_match = attendee_group
            
            if best_match:
                group_mapping[discord_group] = best_match
                if self.debug:
                    self._debug_print(f"Mapped {discord_group} → {best_match} (score: {best_score})")
        
        return group_mapping
    
    def match_by_name(self, discord_name: str, attendee_names: List[str]) -> Tuple[Optional[str], int]:
        """
        Find the best name match from a list of names.
        
        Args:
            discord_name (str): Discord name to match
            attendee_names (List[str]): List of attendee names to match against
            
        Returns:
            Tuple[Optional[str], int]: Best match and score
        """
        if not attendee_names:
            return None, 0
        
        norm_discord = self.normalize_name(discord_name)
        norm_attendees = [self.normalize_name(name) for name in attendee_names]
        
        # Check for exact matches first
        for i, norm_attendee in enumerate(norm_attendees):
            if norm_discord == norm_attendee:
                return attendee_names[i], 100
        
        # Check for name containment
        for i, norm_attendee in enumerate(norm_attendees):
            if (norm_discord in norm_attendee) or (norm_attendee in norm_discord):
                return attendee_names[i], 90
        
        # Fall back to fuzzy matching
        best_match, score = process.extractOne(
            norm_discord, 
            norm_attendees,
            scorer=fuzz.token_set_ratio
        )
        
        if score >= self.threshold:
            idx = norm_attendees.index(best_match)
            return attendee_names[idx], score
        
        return None, score
    
    def find_missing_attendees(self, discord_file: str, attendee_file: str) -> Dict[str, Any]:
        """
        Find attendees missing from Discord using group-first matching.
        
        Args:
            discord_file (str): Path to Discord members file
            attendee_file (str): Path to attendees CSV file
            
        Returns:
            Dict[str, Any]: Results containing matches and missing attendees
        """
        # Load data
        if self.debug:
            self._debug_print(f"Loading Discord members from {discord_file}")
        discord_members, discord_groups = self.load_discord_members(discord_file)
        
        if self.debug:
            self._debug_print(f"Loading attendees from {attendee_file}")
        attendees, attendee_groups = self.load_attendees(attendee_file)
        
        # Map Discord groups to attendee groups
        if self.debug:
            self._debug_print("Mapping Discord groups to attendee groups")
        group_mapping = self.map_groups(discord_groups, attendee_groups)
        
        # Find matches and missing attendees
        matches = []
        missing = []
        missing_by_group = {}
        
        # Create a set to track matched attendees
        matched_attendees = set()
        
        # First pass: match by group and name
        for discord_group, discord_member_ids in discord_groups.items():
            # Find corresponding attendee group
            attendee_group = group_mapping.get(discord_group)
            
            if attendee_group:
                # Get attendees in this group
                group_attendee_ids = attendee_groups.get(attendee_group, [])
                group_attendee_names = [attendees[a_id]['name'] for a_id in group_attendee_ids]
                
                # For each Discord member in this group
                for discord_id in discord_member_ids:
                    discord_member = discord_members[discord_id]
                    
                    # Try to match with an attendee by name
                    best_match, score = self.match_by_name(
                        discord_member['display_name'],
                        group_attendee_names
                    )
                    
                    if best_match and score >= self.threshold:
                        # Find the attendee ID
                        for a_id in group_attendee_ids:
                            if attendees[a_id]['name'] == best_match:
                                matches.append({
                                    'discord_id': discord_id,
                                    'discord_name': discord_member['display_name'],
                                    'attendee_id': a_id,
                                    'attendee_name': best_match,
                                    'group': attendee_group,
                                    'score': score,
                                    'match_type': 'group_and_name'
                                })
                                matched_attendees.add(a_id)
                                break
        
        # Find missing attendees
        for attendee_id, attendee in attendees.items():
            if attendee_id not in matched_attendees:
                missing.append({
                    'attendee_id': attendee_id,
                    'id': attendee.get('id', ''),
                    'name': attendee['name'],
                    'email': attendee.get('email', ''),
                    'phone': attendee.get('phone', ''),
                    'group': attendee['group']
                })
                
                # Organize by group
                group = attendee['group']
                if group not in missing_by_group:
                    missing_by_group[group] = []
                missing_by_group[group].append(attendee)
        
        if self.debug:
            self._debug_print(f"Found {len(matches)} matches")
            self._debug_print(f"Found {len(missing)} missing attendees")
        
        # Return results
        return {
            'matches': matches,
            'missing': missing,
            'missing_by_group': missing_by_group,
            'total_discord': len(discord_members),
            'total_attendees': len(attendees),
            'discord_groups': discord_groups,
            'attendee_groups': attendee_groups,
            'group_mapping': group_mapping
        }
    
    def generate_reports(self, results: Dict[str, Any]) -> Tuple[str, str]:
        """
        Generate text and Excel reports from the results.
        
        Args:
            results (Dict[str, Any]): Results from find_missing_attendees
            
        Returns:
            Tuple[str, str]: Paths to text and Excel reports
        """
        # Create timestamp for filenames
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Ensure output directory exists
        import os
        os.makedirs("output", exist_ok=True)
        
        # Generate text report
        txt_filename = f"output/missing_attendees_group_{timestamp}.txt"
        with open(txt_filename, 'w', encoding='utf-8') as f:
            # Write summary
            f.write(f"Missing Attendees Report (Group-Based) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Discord Members: {results['total_discord']}\n")
            f.write(f"Total Attendees: {results['total_attendees']}\n")
            f.write(f"Missing Attendees: {len(results['missing'])} out of {results['total_attendees']}\n\n")
            
            # Write missing attendees by group
            f.write("MISSING ATTENDEES BY GROUP:\n")
            f.write("-" * 40 + "\n\n")
            
            # Calculate total group sizes for each group in missing_by_group
            group_totals = {}
            for group, _ in results['missing_by_group'].items():
                # Count total attendees in this group
                group_totals[group] = 0
                for attendee_group, attendees in results['attendee_groups'].items():
                    if group == attendee_group:
                        group_totals[group] = len(attendees)
            
            for group, attendees in sorted(results['missing_by_group'].items()):
                total_in_group = group_totals.get(group, 0)
                f.write(f"Group: {group} ({len(attendees)}/{total_in_group} missing)\n")
                # Sort attendees by name
                sorted_attendees = sorted(attendees, key=lambda x: x['name'])
                for i, attendee in enumerate(sorted_attendees):
                    f.write(f"  {i+1}. {attendee['name']}\n")
                f.write("\n")
        
        # Generate Excel report
        excel_filename = f"output/missing_attendees_group_{timestamp}.xlsx"
        
        # Create DataFrames with selected columns for missing attendees
        # Format the data to ensure we have all the fields we want
        formatted_missing = []
        for attendee in results['missing']:
            formatted_missing.append({
                'ID': attendee.get('id', ''),
                'Name': attendee.get('name', ''),
                'Email': attendee.get('email', ''),
                'Phone': attendee.get('phone', ''),
                'Group': attendee.get('group', '')
            })
        
        missing_df = pd.DataFrame(formatted_missing)
        
        # Create Excel writer and save
        with pd.ExcelWriter(excel_filename) as writer:
            missing_df.to_excel(writer, sheet_name='Missing Attendees', index=False)
            
            # Create group mapping sheet
            mapping_data = []
            for discord_group, attendee_group in results['group_mapping'].items():
                mapping_data.append({
                    'Discord Group': discord_group,
                    'Attendee Group': attendee_group,
                    'Discord Members': len(results['discord_groups'].get(discord_group, [])),
                    'Attendees': len(results['attendee_groups'].get(attendee_group, []))
                })
            
            if mapping_data:
                pd.DataFrame(mapping_data).to_excel(writer, sheet_name='Group Mapping', index=False)
        
        return txt_filename, excel_filename

# Example usage
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Find missing attendees using group-based matching")
    parser.add_argument("--discord", default="output/discord_members.txt", help="Path to Discord members file")
    parser.add_argument("--attendees", help="Path to attendees CSV file")
    parser.add_argument("--threshold", type=int, default=70, help="Name matching threshold (0-100)")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    
    args = parser.parse_args()
    
    if not args.attendees:
        # Try to get from environment
        from dotenv import load_dotenv
        load_dotenv()
        args.attendees = os.getenv('ATTENDEE_LIST_PATH')
    
    if not args.attendees:
        print("Error: No attendee file specified. Use --attendees or set ATTENDEE_LIST_PATH in .env")
        exit(1)
    
    # Create matcher
    matcher = GroupMatcher(similarity_threshold=args.threshold, debug=args.debug)
    
    # Find missing attendees
    results = matcher.find_missing_attendees(args.discord, args.attendees)
    
    # Generate reports
    txt_file, excel_file = matcher.generate_reports(results)
    
    print(f"\nFound {len(results['missing'])} missing attendees")
    print(f"Text report saved to: {txt_file}")
    print(f"Excel report saved to: {excel_file}")