from fuzzywuzzy import fuzz, process
import re
import os
import heapq
from typing import Dict, List, Optional, Tuple, Any, Set
from datetime import datetime

class NameMatcher:
    """
    Handles fuzzy string matching between Discord usernames and attendee names.
    """
    
    def __init__(self, similarity_threshold: int = 80, debug: bool = False):
        """
        Initialize the NameMatcher with a similarity threshold.
        
        Args:
            similarity_threshold (int): Minimum similarity score to consider a match (0-100)
            debug (bool): Whether to print detailed debug information
        """
        self.threshold = similarity_threshold
        self.debug = debug
        self.debug_file = None
        self._processed_attendees = {}  # Cache for processed attendee names
        self._processed_discord = {}    # Cache for processed Discord names
    
    def set_debug(self, debug: bool, debug_file: Optional[str] = None):
        """
        Set debug mode on or off and optionally specify a debug output file.
        
        Args:
            debug (bool): Whether to output detailed debug information
            debug_file (Optional[str]): Path to a file to write debug output
        """
        self.debug = debug
        self.debug_file = debug_file
        
        # Initialize debug file if specified
        if debug and debug_file:
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(f"Name Matcher Debug Log - {datetime.now()}\n")
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
        Normalize a name for better comparison by:
        - Converting to lowercase
        - Removing special characters
        - Handling common variations
        - Extracting name after '/' if present
        
        Args:
            name (str): The name to normalize
            
        Returns:
            str: Normalized name
        """
        if not name:
            return ""
            
        # Keep the original for debugging
        original = name
        
        # Extract name after slash if present (for "Group Name / Person Name" format)
        slash_extracted = False
        if '/' in name:
            parts = name.split('/')
            if len(parts) > 1 and len(parts[1].strip()) > 0:
                name = parts[1].strip()
                slash_extracted = True
        
        # Convert to lowercase
        normalized = name.lower()
        
        # Remove Discord discriminators (e.g., #1234)
        if '#' in normalized:
            discriminator_removed = True
            normalized = normalized.split('#')[0]
        else:
            discriminator_removed = False
        
        # Remove special characters
        chars_before = normalized
        for char in ['.', ',', '-', '_', '(', ')', '[', ']', '{', '}', ':', ';']:
            normalized = normalized.replace(char, ' ')
        chars_removed = (chars_before != normalized)
        
        # Trim and remove consecutive spaces
        normalized = ' '.join(normalized.split())
        
        if self.debug:
            changes = []
            if slash_extracted:
                changes.append("slash_extracted")
            if discriminator_removed:
                changes.append("discriminator_removed")
            if chars_removed:
                changes.append("special_chars_removed")
            
            change_str = ", ".join(changes) if changes else "no_changes"
            self._debug_print(f"Normalize: '{original}' -> '{normalized}' ({change_str})")
        
        return normalized
    
    def get_detailed_scores(self, discord_name: str, attendee_name: str) -> Dict[str, int]:
        """
        Get detailed similarity scores between a Discord name and an attendee name.
        
        Args:
            discord_name (str): Discord username
            attendee_name (str): Attendee name from the CSV
            
        Returns:
            Dict[str, int]: Dictionary of different similarity scores
        """
        # Normalize both names
        norm_discord = self.normalize_name(discord_name)
        norm_attendee = self.normalize_name(attendee_name)
        
        # Calculate various similarity scores
        ratio = fuzz.ratio(norm_discord, norm_attendee)
        partial_ratio = fuzz.partial_ratio(norm_discord, norm_attendee)
        token_sort_ratio = fuzz.token_sort_ratio(norm_discord, norm_attendee)
        token_set_ratio = fuzz.token_set_ratio(norm_discord, norm_attendee)
        
        # Simple exact match or contained check
        exact_match = 100 if norm_discord == norm_attendee else 0
        contained = 90 if (norm_discord in norm_attendee or norm_attendee in norm_discord) else 0
        
        return {
            'exact_match': exact_match,
            'contained': contained,
            'ratio': ratio,
            'partial_ratio': partial_ratio,
            'token_sort_ratio': token_sort_ratio,
            'token_set_ratio': token_set_ratio,
            'max_score': max(exact_match, contained, ratio, partial_ratio, token_sort_ratio, token_set_ratio)
        }
    
    def is_match(self, discord_name: str, attendee_name: str) -> Tuple[bool, int, Dict[str, Any]]:
        """
        Check if a Discord username matches an attendee name.
        
        Args:
            discord_name (str): Discord username
            attendee_name (str): Attendee name from the CSV
            
        Returns:
            Tuple[bool, int, Dict[str, Any]]: (is_match, similarity_score, detailed_info)
        """
        # Get detailed scores
        scores = self.get_detailed_scores(discord_name, attendee_name)
        max_score = scores['max_score']
        
        # Track which method gave the max score
        if max_score == scores['exact_match']:
            method = 'exact_match'
        elif max_score == scores['contained']:
            method = 'contained'
        elif max_score == scores['ratio']:
            method = 'ratio'
        elif max_score == scores['partial_ratio']:
            method = 'partial_ratio'
        elif max_score == scores['token_sort_ratio']:
            method = 'token_sort_ratio'
        else:
            method = 'token_set_ratio'
        
        # Create detailed info
        details = {
            'scores': scores,
            'best_method': method,
            'norm_discord': self.normalize_name(discord_name),
            'norm_attendee': self.normalize_name(attendee_name),
            'threshold': self.threshold
        }
        
        if self.debug:
            self._debug_print(f"Match check: '{discord_name}' vs '{attendee_name}'")
            self._debug_print(f"  Normalized: '{details['norm_discord']}' vs '{details['norm_attendee']}'")
            self._debug_print(f"  Scores: {scores}")
            self._debug_print(f"  Best method: {method} with score {max_score}")
            self._debug_print(f"  Result: {'MATCH' if max_score >= self.threshold else 'NO MATCH'}")
        
        return max_score >= self.threshold, max_score, details
    
    def find_best_match(self, discord_name: str, attendee_names: List[str], 
                       return_top_n: int = 1) -> List[Tuple[Optional[str], int, Dict[str, Any]]]:
        """
        Find the best matching attendee name(s) for a Discord username.
        
        Args:
            discord_name (str): Discord username
            attendee_names (List[str]): List of attendee names to compare against
            return_top_n (int): Number of top matches to return
            
        Returns:
            List[Tuple[Optional[str], int, Dict[str, Any]]]: List of (match_name, score, details) tuples
        """
        if not attendee_names:
            return [(None, 0, {})]
        
        # Create a priority queue to store top N matches
        best_matches = []
        
        if self.debug:
            self._debug_print(f"\nFinding best match for Discord name: '{discord_name}'")
            self._debug_print(f"Checking against {len(attendee_names)} attendee names")
        
        # Check against each attendee name
        for attendee_name in attendee_names:
            is_match, score, details = self.is_match(discord_name, attendee_name)
            
            # Use a min heap to keep track of top N matches
            if len(best_matches) < return_top_n:
                heapq.heappush(best_matches, (score, attendee_name, details))
            elif score > best_matches[0][0]:  # If better than worst in top N
                heapq.heappushpop(best_matches, (score, attendee_name, details))
        
        # Convert heap to list of tuples in descending order of score
        results = [(name, score, details) for score, name, details in sorted(best_matches, reverse=True)]
        
        if self.debug:
            for name, score, details in results:
                match_status = "MATCH" if score >= self.threshold else "NO MATCH"
                self._debug_print(f"  Top match: '{name}' with score {score} ({match_status})")
        
        # Filter out matches below threshold if at least one is above
        above_threshold = [r for r in results if r[1] >= self.threshold]
        return above_threshold if above_threshold else results[:1]
    
    def find_matches_for_discord_users(self, 
                                      discord_users: List[str], 
                                      attendee_names: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Find matches for a list of Discord usernames against a list of attendee names.
        
        Args:
            discord_users (List[str]): List of Discord usernames
            attendee_names (List[str]): List of attendee names from the CSV
            
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary mapping Discord usernames to match information
        """
        results = {}
        
        # Pre-process attendee names
        processed_attendees_list = [self.normalize_name(name) for name in attendee_names]
        processed_attendees = dict(zip(processed_attendees_list, attendee_names))
        
        # Export processed names for debugging
        with open("processed_attendees.txt", "w", encoding="utf-8") as f:
            for orig, processed in zip(attendee_names, processed_attendees_list):
                f.write(f"{orig}|{processed}\n")
        
        # Export processed Discord names
        with open("processed_discord.txt", "w", encoding="utf-8") as f:
            for discord_user in discord_users:
                processed = self.normalize_name(discord_user)
                f.write(f"{discord_user}|{processed}\n")
        
        for discord_user in discord_users:
            best_matches = self.find_best_match(discord_user, attendee_names, return_top_n=3)
            if best_matches and best_matches[0][1] >= self.threshold:
                best_match, score, details = best_matches[0]
                results[discord_user] = {
                    'matched': True,
                    'match_name': best_match,
                    'score': score,
                    'details': details,
                    'top_matches': best_matches
                }
            else:
                best_match, score, details = best_matches[0]
                results[discord_user] = {
                    'matched': False,
                    'match_name': None,
                    'closest_name': best_match,
                    'score': score,
                    'details': details,
                    'top_matches': best_matches
                }
        
        # Export closest matches for debugging
        with open("closest_matches.txt", "w", encoding="utf-8") as f:
            f.write("Discord Name|Top 3 Closest Matches\n")
            for discord_user, info in results.items():
                matches_str = ""
                for name, score, _ in info.get('top_matches', []):
                    if name:
                        matches_str += f"{name} ({score}), "
                matches_str = matches_str.rstrip(", ")
                f.write(f"{discord_user}|{matches_str}\n")
        
        return results
    
    def find_missing_attendees(self, 
                             discord_users: List[str], 
                             attendee_names: List[str]) -> List[str]:
        """
        Find attendees who are missing from Discord.
        
        Args:
            discord_users (List[str]): List of Discord usernames
            attendee_names (List[str]): List of attendee names from the CSV
            
        Returns:
            List[str]: List of attendee names who are not found in Discord
        """
        if self.debug:
            self._debug_print(f"\nFinding missing attendees...")
            self._debug_print(f"Discord users: {len(discord_users)}")
            self._debug_print(f"Attendees: {len(attendee_names)}")
        
        # First, find all matches
        matches = self.find_matches_for_discord_users(discord_users, attendee_names)
        
        # Create a list of attendees who were matched
        matched_attendees = [info['match_name'] for info in matches.values() 
                             if info['matched'] and info['match_name']]
        
        if self.debug:
            self._debug_print(f"Matched attendees: {len(matched_attendees)}")
            self._debug_print(f"Missing attendees: {len(attendee_names) - len(matched_attendees)}")
        
        # Return attendees who were not matched
        return [name for name in attendee_names if name not in matched_attendees]
    
    def generate_matching_debug_report(self, discord_users: List[str], 
                                     attendee_names: List[str], 
                                     sample_size: int = 10) -> str:
        """
        Generate a detailed debug report for a sample of attendees.
        
        Args:
            discord_users (List[str]): List of Discord usernames
            attendee_names (List[str]): List of attendee names from the CSV
            sample_size (int): Number of attendees to sample for the report
            
        Returns:
            str: Path to the generated report file
        """
        # Set debug mode for the report
        old_debug = self.debug
        self.debug = True
        
        # Create a timestamp for the filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"matching_debug_{timestamp}.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"Name Matching Debug Report - {datetime.now()}\n")
            f.write(f"Similarity Threshold: {self.threshold}\n")
            f.write(f"Sample Size: {min(sample_size, len(attendee_names))}\n")
            f.write(f"Total Discord Users: {len(discord_users)}\n")
            f.write(f"Total Attendees: {len(attendee_names)}\n")
            f.write("-" * 80 + "\n\n")
            
            # Sample attendees (use all if fewer than sample_size)
            sample = attendee_names[:sample_size] if len(attendee_names) > sample_size else attendee_names
            
            for i, attendee in enumerate(sample):
                f.write(f"ATTENDEE {i+1}: {attendee}\n")
                f.write(f"Normalized: {self.normalize_name(attendee)}\n")
                
                # Find top 3 potential matches from Discord
                temp_debug_file = self.debug_file
                self.debug_file = report_file
                
                best_matches = []
                for discord_user in discord_users:
                    is_match, score, details = self.is_match(discord_user, attendee)
                    best_matches.append((score, discord_user, details))
                
                # Get top 3 matches
                best_matches.sort(reverse=True)
                top_matches = best_matches[:3]
                
                f.write("\nTop 3 Potential Discord Matches:\n")
                for j, (score, discord_user, details) in enumerate(top_matches):
                    match_status = "MATCH" if score >= self.threshold else "NO MATCH"
                    f.write(f"{j+1}. Discord: {discord_user}\n")
                    f.write(f"   Score: {score} ({match_status})\n")
                    f.write(f"   Normalized: {details['norm_discord']}\n")
                    f.write(f"   Method: {details['best_method']}\n")
                    f.write(f"   Ratios: ratio={details['scores']['ratio']}, ")
                    f.write(f"partial={details['scores']['partial_ratio']}, ")
                    f.write(f"token_sort={details['scores']['token_sort_ratio']}, ")
                    f.write(f"token_set={details['scores']['token_set_ratio']}\n")
                
                self.debug_file = temp_debug_file
                f.write("\n" + "-" * 60 + "\n\n")
        
        # Restore original debug setting
        self.debug = old_debug
        
        return report_file

# Example usage
if __name__ == "__main__":
    import sys
    
    # Create a matcher with debug mode
    matcher = NameMatcher(similarity_threshold=80, debug=True)
    
    # Example Discord usernames
    discord_names = ["john_doe", "jane.smith", "mike_jackson123"]
    
    # Example attendee names
    attendee_names = ["John Doe", "Jane Smith", "Michael Jackson", "Sarah Connor"]
    
    if len(sys.argv) > 1 and sys.argv[1] == "--debug":
        # Generate debug report
        report_file = matcher.generate_matching_debug_report(discord_names, attendee_names)
        print(f"Debug report generated: {report_file}")
    else:
        # Find missing attendees
        missing = matcher.find_missing_attendees(discord_names, attendee_names)
        print(f"Missing attendees: {missing}")