"""
Test script to verify email API setup and authentication for multiple providers and test users.
This will test:
1. Authentication with credentials.json for each provider
2. Basic email fetching
3. Email classification (bot vs human)
4. Email actions (mark as read, move to folder, delete, forward, reply, star)
5. Historical email analysis for improved bot detection
6. Saving and loading learned weights
"""

import logging
from email_handler import GmailHandler
from protonmail_handler import ProtonMailHandler
from datetime import datetime
import os
import json
import re

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_email_account(handler, account_name: str):
    """
    Test a single email account.
    
    Args:
        handler: Email handler instance (GmailHandler or ProtonMailHandler)
        account_name: Name of the account being tested
    """
    try:
        logger.info(f"\nTesting {account_name} account...")
        
        # Test authentication
        logger.info("Testing authentication...")
        if not handler.authenticate():
            logger.error(f"❌ Authentication failed for {account_name}")
            return
        
        logger.info("✓ Authentication successful!")
        
        # Check if we have saved weights
        weights_file = f'{account_name.lower().replace(" ", "_")}_weights.json'
        if os.path.exists(weights_file):
            logger.info("\nLoading previously learned weights...")
            if handler.load_learned_weights(weights_file):
                logger.info("✓ Successfully loaded saved weights")
            else:
                logger.info("No valid weights file found, will analyze from scratch")
        
        # Analyze historical emails for better bot detection
        logger.info("\nAnalyzing historical emails to improve bot detection...")
        logger.info("This will analyze patterns in headers, content, timing, and more...")
        
        # Perform detailed historical analysis
        new_weights = handler.analyze_historical_emails(months_back=24)
        
        if new_weights:
            logger.info("✓ Historical analysis complete. Found patterns in:")
            for pattern_type, patterns in new_weights.items():
                if patterns:  # Only show pattern types that have data
                    logger.info(f"  - {pattern_type}: {len(patterns)} patterns")
            
            # Save the learned weights
            logger.info("\nSaving learned weights...")
            if handler.save_learned_weights(weights_file):
                logger.info("✓ Successfully saved weights for future use")
        else:
            logger.warning("No patterns found in historical analysis")
        
        # Fetch recent emails
        logger.info("\nFetching 5 most recent emails...")
        emails = handler.fetch_recent_emails(max_results=5)
        
        # Display results
        logger.info(f"✓ Successfully fetched {len(emails)} emails\n")
        logger.info("Email Summary:")
        logger.info("-" * 80)
        
        for email in emails:
            # Format date nicely
            date_str = email.date.strftime("%Y-%m-%d %H:%M:%S")
            
            # Truncate subject if too long
            subject = (email.subject[:50] + '...') if len(email.subject) > 50 else email.subject
            
            # Get bot detection results
            is_bot, confidence = handler.is_bot_generated(email.headers, email.body_text)
            
            # Get email summary
            summary = email.get_summary(max_length=100)
            
            # Print email details
            logger.info(f"Date: {date_str}")
            logger.info(f"From: {email.sender}")
            logger.info(f"To: {', '.join(email.recipients)}")
            logger.info(f"Subject: {subject}")
            logger.info(f"Summary: {summary}")
            logger.info(f"Classification: {'Bot' if is_bot else 'Human'} generated (confidence: {confidence:.2f})")
            
            # Show which patterns contributed to the classification
            if is_bot:
                logger.info("Bot indicators found:")
                # Check headers
                for header, weight in handler.bot_indicators['headers'].items():
                    if header in email.headers:
                        logger.info(f"  - Header '{header}' (weight: {weight:.2f})")
                
                # Check keywords
                body_lower = email.body_text.lower()
                for keyword, weight in handler.bot_indicators['keywords'].items():
                    if keyword in body_lower:
                        logger.info(f"  - Keyword '{keyword}' (weight: {weight:.2f})")
                
                # Check patterns
                for pattern, weight in handler.bot_indicators['patterns']:
                    if re.search(pattern, email.body_text):
                        logger.info(f"  - Pattern '{pattern}' (weight: {weight:.2f})")
            
            logger.info("-" * 80)
            
            # Test email actions on the first email
            if email == emails[0]:
                logger.info("\nTesting email actions on first email...")
                
                # Test mark as read
                if handler.mark_as_read(email.message_id):
                    logger.info("✓ Successfully marked email as read")
                
                # Test move to folder (using 'Important' as an example)
                if handler.move_to_folder(email.message_id, 'Important'):
                    logger.info("✓ Successfully moved email to Important folder")
                
                # Test starring
                if handler.star_email(email.message_id):
                    logger.info("✓ Successfully starred email")
                
                # Test forward (commented out for safety)
                # if handler.forward_email(email.message_id, "test@example.com", "Please review this email"):
                #     logger.info("✓ Successfully forwarded email")
                
                # Test reply (commented out for safety)
                # if handler.reply_to_email(email.message_id, "Thank you for your email. I will get back to you soon."):
                #     logger.info("✓ Successfully replied to email")
                
                # Test delete (commented out for safety)
                # if handler.delete_email(email.message_id):
                #     logger.info("✓ Successfully moved email to trash")
                
                # Test unstar (commented out for safety)
                # if handler.unstar_email(email.message_id):
                #     logger.info("✓ Successfully unstarred email")
    
    except Exception as e:
        logger.error(f"❌ Error during testing {account_name}: {str(e)}")

def test_multiple_accounts():
    """
    Test multiple email accounts from different providers.
    """
    try:
        # Load account configurations
        with open('account_config.json', 'r') as f:
            accounts = json.load(f)
        
        # Test each account
        for account in accounts:
            provider = account['provider'].lower()
            credentials_path = account['credentials_path']
            
            if provider == 'gmail':
                handler = GmailHandler(credentials_path=credentials_path)
            elif provider == 'protonmail':
                handler = ProtonMailHandler(credentials_path=credentials_path)
            else:
                logger.error(f"Unsupported provider: {provider}")
                continue
            
            test_email_account(handler, account['name'])
    
    except FileNotFoundError:
        logger.error("❌ Error: account_config.json not found!")
        logger.info("Please create account_config.json with your account configurations.")
    except Exception as e:
        logger.error(f"❌ Error during testing: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting multiple account testing...")
    test_multiple_accounts() 