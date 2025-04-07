"""
ProtonMail email handler for the email management agent.
This module provides functionality to interact with ProtonMail accounts.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
import os
from protonmail import ProtonMailAPI  # This would need to be implemented

logger = logging.getLogger(__name__)

class ProtonMailHandler:
    """
    Handles ProtonMail email operations including authentication,
    fetching emails, and performing actions on them.
    """
    
    def __init__(self, credentials_path: str = 'protonmail_credentials.json', 
                 weights_path: str = 'protonmail_weights.json'):
        """
        Initialize the ProtonMail handler.
        
        Args:
            credentials_path: Path to ProtonMail API credentials
            weights_path: Path to save/load learned bot detection weights
        """
        self.credentials_path = credentials_path
        self.weights_path = weights_path
        self.service = None
        self.bot_indicators = {
            'headers': {
                'x-pm-content-encryption': 0.8,
                'x-pm-origin': 0.7,
                'x-pm-transfer-encoding': 0.6
            },
            'keywords': {
                'unsubscribe': 0.9,
                'click here': 0.8,
                'view in browser': 0.7,
                'marketing': 0.8,
                'newsletter': 0.7
            },
            'patterns': [
                (r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', 0.7),
                (r'\[.*?\]', 0.6),  # Square brackets often used in marketing
                (r'\{.*?\}', 0.6)   # Curly braces often used in templates
            ],
            'sender_patterns': {},
            'subject_patterns': {},
            'time_patterns': {},
            'length_patterns': {},
            'link_patterns': {},
            'domain_patterns': {},
            'content_patterns': {},
            'reply_patterns': {},
            'attachment_patterns': {},
            'spacing_patterns': {},
            'signature_patterns': {}
        }
        
        # Try to load saved weights
        self.load_learned_weights(weights_path)
    
    def authenticate(self) -> bool:
        """
        Authenticate with ProtonMail API using credentials.
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            if not os.path.exists(self.credentials_path):
                logger.error(f"Credentials file not found at {self.credentials_path}")
                return False
            
            with open(self.credentials_path, 'r') as f:
                credentials = json.load(f)
            
            # Initialize ProtonMail API client
            self.service = ProtonMailAPI(
                username=credentials['username'],
                password=credentials['password']
            )
            
            # Test the connection
            self.service.ping()
            logger.info("Successfully authenticated with ProtonMail API")
            return True
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def fetch_recent_emails(self, max_results: int = 10) -> List['EmailMessage']:
        """
        Fetch recent emails from the inbox.
        
        Args:
            max_results: Maximum number of emails to fetch
            
        Returns:
            List[EmailMessage]: List of recent emails
        """
        try:
            if not self.service:
                raise Exception("Not authenticated. Call authenticate() first.")
            
            # Fetch recent messages
            messages = self.service.get_messages(limit=max_results)
            
            email_list = []
            for msg in messages:
                email = EmailMessage(
                    message_id=msg['id'],
                    sender=msg['from'],
                    recipients=msg['to'],
                    subject=msg['subject'],
                    body_text=msg['body'],
                    date=datetime.fromtimestamp(msg['time']),
                    headers=msg['headers']
                )
                email_list.append(email)
            
            return email_list
            
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []
    
    def is_bot_generated(self, headers: Dict[str, str], body_text: str) -> Tuple[bool, float]:
        """
        Determine if an email is likely bot-generated using multiple indicators.
        
        Args:
            headers: Email headers
            body_text: Email body text
            
        Returns:
            Tuple[bool, float]: (is_bot, confidence_score)
        """
        try:
            total_score = 0.0
            indicators_checked = 0
            
            # Check headers
            for header, weight in self.bot_indicators['headers'].items():
                if header in headers:
                    total_score += weight
                    indicators_checked += 1
            
            # Check keywords
            body_lower = body_text.lower()
            for keyword, weight in self.bot_indicators['keywords'].items():
                if keyword in body_lower:
                    total_score += weight
                    indicators_checked += 1
            
            # Check patterns
            for pattern, weight in self.bot_indicators['patterns']:
                if re.search(pattern, body_text):
                    total_score += weight
                    indicators_checked += 1
            
            # Calculate confidence score
            confidence = total_score / indicators_checked if indicators_checked > 0 else 0.0
            
            # Consider it bot-generated if confidence > 0.5
            return confidence > 0.5, confidence
            
        except Exception as e:
            logger.error(f"Error in bot detection: {e}")
            return False, 0.0
    
    def mark_as_read(self, message_id: str) -> bool:
        """
        Mark an email as read.
        
        Args:
            message_id: ID of the email to mark as read
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.service:
                raise Exception("Not authenticated. Call authenticate() first.")
            
            self.service.mark_as_read(message_id)
            return True
            
        except Exception as e:
            logger.error(f"Error marking email as read: {e}")
            return False
    
    def move_to_folder(self, message_id: str, folder_name: str) -> bool:
        """
        Move an email to a specific folder.
        
        Args:
            message_id: ID of the email to move
            folder_name: Name of the folder to move to
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.service:
                raise Exception("Not authenticated. Call authenticate() first.")
            
            self.service.move_to_folder(message_id, folder_name)
            return True
            
        except Exception as e:
            logger.error(f"Error moving email to folder: {e}")
            return False
    
    def delete_email(self, message_id: str) -> bool:
        """
        Move an email to trash.
        
        Args:
            message_id: ID of the email to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.service:
                raise Exception("Not authenticated. Call authenticate() first.")
            
            self.service.move_to_trash(message_id)
            return True
            
        except Exception as e:
            logger.error(f"Error deleting email: {e}")
            return False
    
    def forward_email(self, message_id: str, to_address: str, message: Optional[str] = None) -> bool:
        """
        Forward an email to another address.
        
        Args:
            message_id: ID of the email to forward
            to_address: Email address to forward to
            message: Optional message to include with the forward
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.service:
                raise Exception("Not authenticated. Call authenticate() first.")
            
            self.service.forward(message_id, to_address, message)
            return True
            
        except Exception as e:
            logger.error(f"Error forwarding email: {e}")
            return False
    
    def reply_to_email(self, message_id: str, reply_text: str) -> bool:
        """
        Reply to an email.
        
        Args:
            message_id: ID of the email to reply to
            reply_text: Text of the reply
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.service:
                raise Exception("Not authenticated. Call authenticate() first.")
            
            self.service.reply(message_id, reply_text)
            return True
            
        except Exception as e:
            logger.error(f"Error replying to email: {e}")
            return False
    
    def star_email(self, message_id: str) -> bool:
        """
        Star an email.
        
        Args:
            message_id: ID of the email to star
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.service:
                raise Exception("Not authenticated. Call authenticate() first.")
            
            self.service.star(message_id)
            return True
            
        except Exception as e:
            logger.error(f"Error starring email: {e}")
            return False
    
    def unstar_email(self, message_id: str) -> bool:
        """
        Remove star from an email.
        
        Args:
            message_id: ID of the email to unstar
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.service:
                raise Exception("Not authenticated. Call authenticate() first.")
            
            self.service.unstar(message_id)
            return True
            
        except Exception as e:
            logger.error(f"Error unstarring email: {e}")
            return False
    
    def analyze_historical_emails(self, months_back: int = 24) -> Dict[str, float]:
        """
        Analyze historical emails to improve bot detection accuracy.
        
        Args:
            months_back: Number of months of history to analyze
            
        Returns:
            Dict[str, float]: Updated weights for bot detection
        """
        try:
            if not self.service:
                raise Exception("Not authenticated. Call authenticate() first.")
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=months_back*30)
            
            # Fetch messages in date range
            messages = self.service.get_messages(
                start_date=start_date.timestamp(),
                end_date=end_date.timestamp(),
                limit=500
            )
            
            logger.info(f"Analyzing {len(messages)} historical emails...")
            
            # Initialize pattern counters
            pattern_counts = {
                'headers': {},
                'keywords': {},
                'patterns': {},
                'sender_patterns': {},
                'subject_patterns': {},
                'time_patterns': {},
                'length_patterns': {},
                'link_patterns': {},
                'domain_patterns': {},
                'content_patterns': {},
                'reply_patterns': {},
                'attachment_patterns': {},
                'spacing_patterns': {},
                'signature_patterns': {}
            }
            
            # Analyze each message
            for msg in messages:
                # Extract sender domain
                sender = msg['from']
                if '@' in sender:
                    domain = sender.split('@')[1].lower()
                    pattern_counts['domain_patterns'][domain] = pattern_counts['domain_patterns'].get(domain, 0) + 1
                
                # Analyze content patterns
                body_text = msg['body']
                if 'unsubscribe' in body_text.lower():
                    pattern_counts['content_patterns']['unsubscribe'] = pattern_counts['content_patterns'].get('unsubscribe', 0) + 1
                
                # Add more pattern analysis here...
                
            # Calculate new weights based on frequency
            total_messages = len(messages)
            new_weights = {}
            
            # Calculate weights for each pattern type
            for pattern_type, counts in pattern_counts.items():
                new_weights[pattern_type] = {}
                for pattern, count in counts.items():
                    frequency = count / total_messages
                    new_weights[pattern_type][pattern] = min(1.0, frequency * 2)
            
            # Update the bot indicators
            self.bot_indicators.update(new_weights)
            
            # Save the learned weights
            self.save_learned_weights(self.weights_path)
            
            logger.info("Historical email analysis complete. Bot detection weights updated.")
            return new_weights
            
        except Exception as e:
            logger.error(f"Error analyzing historical emails: {e}")
            return {}
    
    def save_learned_weights(self, file_path: str) -> bool:
        """
        Save the learned bot detection weights to a file.
        
        Args:
            file_path: Path to save the weights to
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            weights_data = {
                'weights': self.bot_indicators,
                'last_updated': datetime.now().isoformat(),
                'version': '1.0'
            }
            
            with open(file_path, 'w') as f:
                json.dump(weights_data, f, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving weights: {e}")
            return False
    
    def load_learned_weights(self, file_path: str) -> bool:
        """
        Load previously learned bot detection weights from a file.
        
        Args:
            file_path: Path to load the weights from
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                logger.warning(f"Weights file {file_path} not found. Using default weights.")
                return False
            
            with open(file_path, 'r') as f:
                weights_data = json.load(f)
            
            if 'weights' in weights_data:
                self.bot_indicators.update(weights_data['weights'])
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error loading weights: {e}")
            return False 