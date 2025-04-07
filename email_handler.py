"""
Email Handler for Email Management Agent
This module handles email access, authentication, and basic email operations.
"""

import os
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class EmailMessage:
    """
    Data class to store email information in a standardized format.
    This will work for both Gmail and ProtonMail messages.
    """
    message_id: str
    sender: str
    recipients: List[str]  # List of email recipients
    subject: str
    date: datetime
    body_text: str
    body_html: Optional[str]
    is_human_generated: Optional[bool] = None
    importance_score: Optional[float] = None
    headers: Dict[str, str] = None
    labels: List[str] = None
    thread_id: str = None  # For thread-related operations

    def get_summary(self, max_length: int = 100) -> str:
        """
        Returns a short summary of the email.
        
        Args:
            max_length: Maximum length of the summary
            
        Returns:
            str: A brief summary of the email content
        """
        # Clean and truncate the body text
        clean_text = ' '.join(self.body_text.split())
        if len(clean_text) > max_length:
            clean_text = clean_text[:max_length] + '...'
        return clean_text

class GmailHandler:
    """
    Handles Gmail API operations including authentication and email fetching.
    
    Example usage:
        gmail = GmailHandler()
        gmail.authenticate()
        messages = gmail.fetch_recent_emails(max_results=10)
    """
    
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify'
    ]
    
    def __init__(self, credentials_path: str = 'credentials.json', 
                 token_path: str = 'token.pickle',
                 weights_path: str = 'bot_weights.json'):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.weights_path = weights_path
        self.service = None
        
        # Initialize bot indicators with default weights
        self.bot_indicators = {
            'headers': {
                'list-unsubscribe': 0.8,
                'precedence: bulk': 0.9,
                'x-marketing': 0.85,
                'x-campaign': 0.85,
                'x-mailer': 0.7,
                'auto-submitted': 0.9,
                'x-autoreply': 0.8
            },
            'keywords': {
                'unsubscribe': 0.7,
                'newsletter': 0.8,
                'marketing': 0.75,
                'subscription': 0.7,
                'loan': 0.9,
                'mortgage': 0.9,
                'credit': 0.9,
                'promotion': 0.8,
                'special offer': 0.8,
                'click here': 0.7
            },
            'patterns': {
                r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+': 0.6,
                r'[0-9]{3}-[0-9]{3}-[0-9]{4}': 0.5,
                r'\$\d+\.?\d*': 0.5
            },
            'sender_patterns': {},
            'subject_patterns': {},
            'time_patterns': {},
            'length_patterns': {},
            'link_patterns': {},
            'domain_patterns': {}
        }
        
        # Try to load saved weights
        self.load_learned_weights(weights_path)
        
    def authenticate(self) -> None:
        """
        Handles Gmail API authentication using OAuth 2.0.
        Saves credentials to token.pickle for future use.
        """
        creds = None
        
        # Load existing token if available
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # Refresh token if expired
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Error refreshing credentials: {e}")
                creds = None
        
        # If no valid credentials available, get new ones
        if not creds:
            if not os.path.exists(self.credentials_path):
                raise FileNotFoundError(
                    "credentials.json not found. Please download it from Google Cloud Console."
                )
            
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_path, self.SCOPES)
            creds = flow.run_local_server(port=0)
            
            # Save credentials for future use
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('gmail', 'v1', credentials=creds)
        logger.info("Successfully authenticated with Gmail API")

    def is_bot_generated(self, headers: Dict[str, str], body: str) -> Tuple[bool, float]:
        """
        Determines if an email is likely bot-generated based on headers and content.
        Returns a tuple of (is_bot, confidence_score).
        
        Args:
            headers: Email headers dictionary
            body: Email body text
        
        Returns:
            Tuple[bool, float]: (True if likely bot-generated, confidence score 0-1)
        """
        confidence_score = 0.0
        max_score = 0.0
        
        # Check headers
        for header, weight in self.bot_indicators['headers'].items():
            if any(h.lower() == header.lower() for h in headers.keys()):
                confidence_score += weight
                max_score += weight
        
        # Check content keywords
        body_lower = body.lower()
        for keyword, weight in self.bot_indicators['keywords'].items():
            if keyword in body_lower:
                confidence_score += weight
                max_score += weight
        
        # Check patterns
        for pattern, weight in self.bot_indicators['patterns'].items():
            if re.search(pattern, body):
                confidence_score += weight
                max_score += weight
        
        # Normalize score
        final_score = confidence_score / max_score if max_score > 0 else 0
        
        # Consider email length and structure
        if len(body) > 1000:  # Longer emails are more likely to be marketing
            final_score += 0.1
        
        # Cap the score at 1.0
        final_score = min(final_score, 1.0)
        
        return final_score > 0.5, final_score

    def mark_as_read(self, message_id: str) -> bool:
        """
        Marks an email as read.
        
        Args:
            message_id: The ID of the email to mark as read
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            logger.info(f"Marked email {message_id} as read")
            return True
        except Exception as e:
            logger.error(f"Error marking email as read: {e}")
            return False

    def move_to_folder(self, message_id: str, folder_name: str) -> bool:
        """
        Moves an email to a specified folder/label.
        
        Args:
            message_id: The ID of the email to move
            folder_name: The name of the folder/label to move to
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # First, get all labels to find the correct one
            labels = self.service.users().labels().list(userId='me').execute()
            label_id = None
            
            for label in labels.get('labels', []):
                if label['name'].lower() == folder_name.lower():
                    label_id = label['id']
                    break
            
            if not label_id:
                logger.error(f"Folder/label '{folder_name}' not found")
                return False
            
            # Move the email
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': [label_id]}
            ).execute()
            
            logger.info(f"Moved email {message_id} to {folder_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error moving email: {e}")
            return False

    def delete_email(self, message_id: str) -> bool:
        """
        Moves an email to the trash.
        
        Args:
            message_id: The ID of the email to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.service.users().messages().trash(
                userId='me',
                id=message_id
            ).execute()
            logger.info(f"Moved email {message_id} to trash")
            return True
        except Exception as e:
            logger.error(f"Error deleting email: {e}")
            return False

    def forward_email(self, message_id: str, to_address: str, note: str = "") -> bool:
        """
        Forwards an email to a specified address.
        
        Args:
            message_id: The ID of the email to forward
            to_address: The email address to forward to
            note: Optional note to include with the forward
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the original message
            message = self.service.users().messages().get(
                userId='me', id=message_id, format='raw').execute()
            
            # Create the forward message
            forward_message = {
                'raw': message['raw'],
                'threadId': message.get('threadId'),
                'labelIds': ['SENT']
            }
            
            # Add the note if provided
            if note:
                forward_message['raw'] = self._add_note_to_message(
                    forward_message['raw'], note)
            
            # Send the forward
            self.service.users().messages().send(
                userId='me', body=forward_message).execute()
            
            logger.info(f"Successfully forwarded email {message_id} to {to_address}")
            return True
            
        except Exception as e:
            logger.error(f"Error forwarding email: {e}")
            return False

    def reply_to_email(self, message_id: str, reply_text: str) -> bool:
        """
        Sends a reply to an email.
        
        Args:
            message_id: The ID of the email to reply to
            reply_text: The text of the reply
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the original message
            message = self.service.users().messages().get(
                userId='me', id=message_id, format='metadata').execute()
            
            # Get the thread ID and subject
            thread_id = message.get('threadId')
            subject = next(
                (h['value'] for h in message['payload']['headers'] 
                 if h['name'].lower() == 'subject'),
                'Re: ' + message.get('subject', '')
            )
            
            # Create the reply message
            reply_message = {
                'threadId': thread_id,
                'raw': self._create_message(
                    to=message['payload']['headers'][0]['value'],  # Original sender
                    subject=subject,
                    message_text=reply_text
                )
            }
            
            # Send the reply
            self.service.users().messages().send(
                userId='me', body=reply_message).execute()
            
            logger.info(f"Successfully replied to email {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error replying to email: {e}")
            return False

    def _add_note_to_message(self, raw_message: str, note: str) -> str:
        """Adds a note to a raw email message."""
        import base64
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Decode the raw message
        msg_str = base64.urlsafe_b64decode(raw_message).decode('utf-8')
        
        # Create a new message with the note
        msg = MIMEMultipart()
        msg.attach(MIMEText(note, 'plain'))
        
        # Add the original message
        msg.attach(MIMEText(msg_str, 'plain'))
        
        return base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')

    def _create_message(self, to: str, subject: str, message_text: str) -> str:
        """Creates a base64 encoded email message."""
        from email.mime.text import MIMEText
        import base64
        
        message = MIMEText(message_text)
        message['to'] = to
        message['subject'] = subject
        
        return base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

    def fetch_recent_emails(self, max_results: int = 50) -> List[EmailMessage]:
        """
        Fetches recent emails from Gmail.
        
        Args:
            max_results: Maximum number of emails to fetch
            
        Returns:
            List[EmailMessage]: List of standardized email messages
        """
        try:
            # Get message list
            results = self.service.users().messages().list(
                userId='me', maxResults=max_results).execute()
            messages = results.get('messages', [])
            
            if not messages:
                logger.info("No messages found.")
                return []
            
            email_messages = []
            for message in messages:
                msg = self.service.users().messages().get(
                    userId='me', id=message['id'], format='full').execute()
                
                # Extract headers
                headers = {}
                for header in msg['payload']['headers']:
                    headers[header['name'].lower()] = header['value']
                
                # Extract recipients
                recipients = []
                if 'to' in headers:
                    recipients.extend([addr.strip() for addr in headers['to'].split(',')])
                if 'cc' in headers:
                    recipients.extend([addr.strip() for addr in headers['cc'].split(',')])
                
                # Extract body
                body_text = self._get_body_text(msg['payload'])
                body_html = self._get_body_html(msg['payload'])
                
                # Create EmailMessage object
                email_msg = EmailMessage(
                    message_id=msg['id'],
                    sender=headers.get('from', ''),
                    recipients=recipients,
                    subject=headers.get('subject', ''),
                    date=datetime.fromtimestamp(int(msg['internalDate'])/1000),
                    body_text=body_text,
                    body_html=body_html,
                    headers=headers,
                    is_human_generated=not self.is_bot_generated(headers, body_text)[0],
                    thread_id=msg.get('threadId')
                )
                
                email_messages.append(email_msg)
            
            return email_messages
            
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []

    def _get_body_text(self, payload) -> str:
        """Extract text body from message payload."""
        if payload.get('body', {}).get('data'):
            return self._decode_body(payload['body']['data'])
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    return self._decode_body(part['body'].get('data', ''))
        
        return ''

    def _get_body_html(self, payload) -> Optional[str]:
        """Extract HTML body from message payload."""
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/html':
                    return self._decode_body(part['body'].get('data', ''))
        return None

    def _decode_body(self, data: str) -> str:
        """Decode base64 body content."""
        import base64
        if not data:
            return ''
        return base64.urlsafe_b64decode(data).decode('utf-8')

    def star_email(self, message_id: str) -> bool:
        """
        Stars an email (adds the 'STARRED' label).
        
        Args:
            message_id: The ID of the email to star
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': ['STARRED']}
            ).execute()
            logger.info(f"Starred email {message_id}")
            return True
        except Exception as e:
            logger.error(f"Error starring email: {e}")
            return False

    def unstar_email(self, message_id: str) -> bool:
        """
        Removes the star from an email (removes the 'STARRED' label).
        
        Args:
            message_id: The ID of the email to unstar
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['STARRED']}
            ).execute()
            logger.info(f"Unstarred email {message_id}")
            return True
        except Exception as e:
            logger.error(f"Error unstarring email: {e}")
            return False

    def save_learned_weights(self, file_path: str = 'bot_weights.json') -> bool:
        """
        Saves the learned bot detection weights to a JSON file.
        
        Args:
            file_path: Path to save the weights file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            import json
            from datetime import datetime
            
            # Add metadata about when the weights were saved
            weights_data = {
                'weights': self.bot_indicators,
                'metadata': {
                    'last_updated': datetime.now().isoformat(),
                    'version': '1.0'
                }
            }
            
            with open(file_path, 'w') as f:
                json.dump(weights_data, f, indent=2)
            
            logger.info(f"Successfully saved bot detection weights to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving bot detection weights: {e}")
            return False

    def load_learned_weights(self, file_path: str = 'bot_weights.json') -> bool:
        """
        Loads previously learned bot detection weights from a JSON file.
        
        Args:
            file_path: Path to the weights file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            import json
            import os
            
            if not os.path.exists(file_path):
                logger.warning(f"Weights file {file_path} not found. Using default weights.")
                return False
            
            with open(file_path, 'r') as f:
                weights_data = json.load(f)
            
            # Update the bot indicators with loaded weights
            self.bot_indicators.update(weights_data['weights'])
            
            logger.info(f"Successfully loaded bot detection weights from {file_path}")
            logger.info(f"Last updated: {weights_data['metadata']['last_updated']}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading bot detection weights: {e}")
            return False

    def analyze_historical_emails(self, months_back: int = 24) -> Dict[str, float]:
        """
        Analyzes historical emails to improve bot detection accuracy.
        This function looks at emails from the past specified months
        and updates the bot detection weights based on patterns found.
        
        Args:
            months_back: Number of months of history to analyze
            
        Returns:
            Dict[str, float]: Updated weights for bot detection
        """
        try:
            # Calculate the date range
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=months_back*30)
            
            # Query for messages in the date range
            query = f'after:{int(start_date.timestamp())} before:{int(end_date.timestamp())}'
            
            # Get all messages in the date range
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=500  # Adjust based on your needs
            ).execute()
            
            messages = results.get('messages', [])
            logger.info(f"Analyzing {len(messages)} historical emails...")
            
            # Initialize counters for pattern analysis
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
            for message in messages:
                msg = self.service.users().messages().get(
                    userId='me', id=message['id'], format='full').execute()
                
                # Extract headers
                headers = {}
                for header in msg['payload']['headers']:
                    headers[header['name'].lower()] = header['value']
                
                # Extract body
                body_text = self._get_body_text(msg['payload'])
                
                # Extract sender domain
                sender = headers.get('from', '')
                if '@' in sender:
                    domain = sender.split('@')[1].lower()
                    pattern_counts['domain_patterns'][domain] = pattern_counts['domain_patterns'].get(domain, 0) + 1
                
                # Analyze sender patterns
                sender_name = sender.split('<')[0].strip()
                if sender_name:
                    pattern_counts['sender_patterns'][sender_name] = pattern_counts['sender_patterns'].get(sender_name, 0) + 1
                
                # Analyze subject patterns
                subject = headers.get('subject', '')
                if subject:
                    # Look for common subject patterns
                    if 're:' in subject.lower():
                        pattern_counts['subject_patterns']['re:'] = pattern_counts['subject_patterns'].get('re:', 0) + 1
                    if 'fw:' in subject.lower():
                        pattern_counts['subject_patterns']['fw:'] = pattern_counts['subject_patterns'].get('fw:', 0) + 1
                    # Look for marketing patterns
                    if any(word in subject.lower() for word in ['sale', 'offer', 'discount', 'limited time']):
                        pattern_counts['subject_patterns']['marketing'] = pattern_counts['subject_patterns'].get('marketing', 0) + 1
                
                # Analyze time patterns
                date = datetime.fromtimestamp(int(msg['internalDate'])/1000)
                hour = date.hour
                pattern_counts['time_patterns'][hour] = pattern_counts['time_patterns'].get(hour, 0) + 1
                
                # Analyze length patterns
                body_length = len(body_text)
                length_category = 'short' if body_length < 100 else 'medium' if body_length < 500 else 'long'
                pattern_counts['length_patterns'][length_category] = pattern_counts['length_patterns'].get(length_category, 0) + 1
                
                # Analyze content patterns
                # Check for common bot-generated content patterns
                if 'unsubscribe' in body_text.lower():
                    pattern_counts['content_patterns']['unsubscribe'] = pattern_counts['content_patterns'].get('unsubscribe', 0) + 1
                if 'click here' in body_text.lower():
                    pattern_counts['content_patterns']['click_here'] = pattern_counts['content_patterns'].get('click_here', 0) + 1
                if 'view in browser' in body_text.lower():
                    pattern_counts['content_patterns']['view_in_browser'] = pattern_counts['content_patterns'].get('view_in_browser', 0) + 1
                
                # Analyze reply patterns
                if '>' in body_text:  # Common reply indicator
                    pattern_counts['reply_patterns']['quoted'] = pattern_counts['reply_patterns'].get('quoted', 0) + 1
                if 'On ' in body_text and 'wrote:' in body_text:  # Common email client reply format
                    pattern_counts['reply_patterns']['email_client'] = pattern_counts['reply_patterns'].get('email_client', 0) + 1
                
                # Analyze attachment patterns
                if 'parts' in msg['payload']:
                    for part in msg['payload']['parts']:
                        if 'filename' in part:
                            pattern_counts['attachment_patterns']['has_attachment'] = pattern_counts['attachment_patterns'].get('has_attachment', 0) + 1
                            break
                
                # Analyze spacing patterns
                lines = body_text.split('\n')
                avg_line_length = sum(len(line) for line in lines) / len(lines) if lines else 0
                spacing_category = 'dense' if avg_line_length > 80 else 'normal' if avg_line_length > 40 else 'sparse'
                pattern_counts['spacing_patterns'][spacing_category] = pattern_counts['spacing_patterns'].get(spacing_category, 0) + 1
                
                # Analyze signature patterns
                if '--' in body_text or 'Best regards' in body_text or 'Thanks' in body_text:
                    pattern_counts['signature_patterns']['has_signature'] = pattern_counts['signature_patterns'].get('has_signature', 0) + 1
                
                # Count header patterns
                for header in headers:
                    pattern_counts['headers'][header] = pattern_counts['headers'].get(header, 0) + 1
                
                # Count keyword patterns
                for keyword in self.bot_indicators['keywords']:
                    if keyword in body_text.lower():
                        pattern_counts['keywords'][keyword] = pattern_counts['keywords'].get(keyword, 0) + 1
                
                # Count regex patterns
                for pattern in self.bot_indicators['patterns']:
                    if re.search(pattern, body_text):
                        pattern_counts['patterns'][pattern] = pattern_counts['patterns'].get(pattern, 0) + 1
                
                # Analyze link patterns
                links = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', body_text)
                link_count = len(links)
                link_category = 'none' if link_count == 0 else 'few' if link_count < 3 else 'many'
                pattern_counts['link_patterns'][link_category] = pattern_counts['link_patterns'].get(link_category, 0) + 1
            
            # Calculate new weights based on frequency
            total_messages = len(messages)
            new_weights = {
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
            
            # Calculate header weights
            for header, count in pattern_counts['headers'].items():
                frequency = count / total_messages
                # Higher frequency = higher weight for bot detection
                new_weights['headers'][header] = min(1.0, frequency * 2)
            
            # Calculate keyword weights
            for keyword, count in pattern_counts['keywords'].items():
                frequency = count / total_messages
                new_weights['keywords'][keyword] = min(1.0, frequency * 2)
            
            # Calculate pattern weights
            for pattern, count in pattern_counts['patterns'].items():
                frequency = count / total_messages
                new_weights['patterns'][pattern] = min(1.0, frequency * 2)
            
            # Calculate sender pattern weights
            for sender, count in pattern_counts['sender_patterns'].items():
                frequency = count / total_messages
                # Very frequent senders might be bots
                new_weights['sender_patterns'][sender] = min(1.0, frequency * 3)
            
            # Calculate subject pattern weights
            for pattern, count in pattern_counts['subject_patterns'].items():
                frequency = count / total_messages
                new_weights['subject_patterns'][pattern] = min(1.0, frequency * 2)
            
            # Calculate time pattern weights
            for hour, count in pattern_counts['time_patterns'].items():
                frequency = count / total_messages
                # Emails at unusual hours might be automated
                if hour < 6 or hour > 22:  # Late night/early morning
                    new_weights['time_patterns'][hour] = min(1.0, frequency * 2)
            
            # Calculate length pattern weights
            for length, count in pattern_counts['length_patterns'].items():
                frequency = count / total_messages
                # Very short or very long emails might be automated
                if length in ['short', 'long']:
                    new_weights['length_patterns'][length] = min(1.0, frequency * 1.5)
            
            # Calculate link pattern weights
            for pattern, count in pattern_counts['link_patterns'].items():
                frequency = count / total_messages
                # Emails with many links might be marketing
                if pattern == 'many':
                    new_weights['link_patterns'][pattern] = min(1.0, frequency * 2)
            
            # Calculate domain pattern weights
            for domain, count in pattern_counts['domain_patterns'].items():
                frequency = count / total_messages
                # Frequent domains might be automated
                new_weights['domain_patterns'][domain] = min(1.0, frequency * 2)
            
            # Calculate content pattern weights
            for pattern, count in pattern_counts['content_patterns'].items():
                frequency = count / total_messages
                # Marketing content patterns are strong indicators
                new_weights['content_patterns'][pattern] = min(1.0, frequency * 2.5)
            
            # Calculate reply pattern weights
            for pattern, count in pattern_counts['reply_patterns'].items():
                frequency = count / total_messages
                # Reply patterns indicate human interaction
                new_weights['reply_patterns'][pattern] = min(1.0, frequency * 0.5)  # Lower weight as it indicates human
            
            # Calculate attachment pattern weights
            for pattern, count in pattern_counts['attachment_patterns'].items():
                frequency = count / total_messages
                # Attachments are more common in human emails
                new_weights['attachment_patterns'][pattern] = min(1.0, frequency * 0.3)  # Lower weight as it indicates human
            
            # Calculate spacing pattern weights
            for pattern, count in pattern_counts['spacing_patterns'].items():
                frequency = count / total_messages
                # Dense spacing might indicate automated content
                if pattern == 'dense':
                    new_weights['spacing_patterns'][pattern] = min(1.0, frequency * 1.5)
            
            # Calculate signature pattern weights
            for pattern, count in pattern_counts['signature_patterns'].items():
                frequency = count / total_messages
                # Signatures indicate human emails
                new_weights['signature_patterns'][pattern] = min(1.0, frequency * 0.4)  # Lower weight as it indicates human
            
            # Update the bot indicators with new weights
            self.bot_indicators.update(new_weights)
            
            # After updating weights, save them
            self.save_learned_weights(self.weights_path)
            
            logger.info("Historical email analysis complete. Bot detection weights updated.")
            return new_weights
            
        except Exception as e:
            logger.error(f"Error analyzing historical emails: {e}")
            return {}