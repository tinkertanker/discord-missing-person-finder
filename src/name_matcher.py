from fuzzywuzzy import fuzz, process
from typing import Dict, List, Optional, Tuple, Any

class NameMatcher:
    """
    Handles fuzzy string matching between Discord usernames and attendee names.
    """
    
    def __init__(self, similarity_threshold: int = 80):
        """
        Initialize the NameMatcher with a similarity threshold.
        
        Args:
            similarity_threshold (int): Minimum similarity score to consider a match (0-100)
        """
        self.threshold = similarity_threshold
    
    def normalize_name(self, name: str) -> str:
        """
        Normalize a name for better comparison by:
        - Converting to lowercase
        - Removing special characters
        - Handling common variations
        
        Args:
            name (str): The name to normalize
            
        Returns:
            str: Normalized name
        """
        # Convert to lowercase
        normalized = name.lower()
        
        # Remove Discord discriminators (e.g., #1234)
        if '#' in normalized:
            normalized = normalized.split('#')[0]
        
        # Remove special characters
        for char in ['.', ',', '-', '_', '(', ')', '[', ']', '{', '}']:
            normalized = normalized.replace(char, ' ')
        
        # Trim and remove consecutive spaces
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def is_match(self, discord_name: str, attendee_name: str) -> Tuple[bool, int]:
        """
        Check if a Discord username matches an attendee name.
        
        Args:
            discord_name (str): Discord username
            attendee_name (str): Attendee name from the CSV
            
        Returns:
            Tuple[bool, int]: (is_match, similarity_score)
        """
        # Normalize both names
        norm_discord = self.normalize_name(discord_name)
        norm_attendee = self.normalize_name(attendee_name)
        
        # First check exact match after normalization
        if norm_discord == norm_attendee:
            return True, 100
        
        # Check if one name is fully contained in the other
        if norm_discord in norm_attendee or norm_attendee in norm_discord:
            contained_score = 90
            return contained_score >= self.threshold, contained_score
        
        # Calculate various similarity scores
        ratio = fuzz.ratio(norm_discord, norm_attendee)
        partial_ratio = fuzz.partial_ratio(norm_discord, norm_attendee)
        token_sort_ratio = fuzz.token_sort_ratio(norm_discord, norm_attendee)
        token_set_ratio = fuzz.token_set_ratio(norm_discord, norm_attendee)
        
        # Use the highest score
        score = max(ratio, partial_ratio, token_sort_ratio, token_set_ratio)
        
        return score >= self.threshold, score
    
    def find_best_match(self, discord_name: str, attendee_names: List[str]) -> Tuple[Optional[str], int]:
        """
        Find the best matching attendee name for a Discord username.
        
        Args:
            discord_name (str): Discord username
            attendee_names (List[str]): List of attendee names to compare against
            
        Returns:
            Tuple[Optional[str], int]: (best_match_name, similarity_score)
                                       or (None, 0) if no match found
        """
        if not attendee_names:
            return None, 0
        
        norm_discord = self.normalize_name(discord_name)
        
        # Find best match using process.extractOne
        best_match, score = process.extractOne(
            norm_discord, 
            [self.normalize_name(name) for name in attendee_names],
            scorer=fuzz.token_set_ratio
        )
        
        # Find the original attendee name based on the normalized match
        for name in attendee_names:
            if self.normalize_name(name) == best_match:
                if score >= self.threshold:
                    return name, score
                break
        
        return None, score
    
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
                {
                    'discord_username': {
                        'matched': True/False,
                        'match_name': attendee_name or None,
                        'score': similarity_score
                    },
                    ...
                }
        """
        results = {}
        
        for discord_user in discord_users:
            match_name, score = self.find_best_match(discord_user, attendee_names)
            results[discord_user] = {
                'matched': match_name is not None,
                'match_name': match_name,
                'score': score
            }
            
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
        # First, find all matches
        matches = self.find_matches_for_discord_users(discord_users, attendee_names)
        
        # Create a list of attendees who were matched
        matched_attendees = [info['match_name'] for info in matches.values() 
                             if info['matched'] and info['match_name']]
        
        # Return attendees who were not matched
        return [name for name in attendee_names if name not in matched_attendees]

# Example usage
if __name__ == "__main__":
    matcher = NameMatcher(similarity_threshold=80)
    
    # Example Discord usernames
    discord_names = ["john_doe", "jane.smith", "mike_jackson123"]
    
    # Example attendee names
    attendee_names = ["John Doe", "Jane Smith", "Michael Jackson", "Sarah Connor"]
    
    # Find missing attendees
    missing = matcher.find_missing_attendees(discord_names, attendee_names)
    print(f"Missing attendees: {missing}")