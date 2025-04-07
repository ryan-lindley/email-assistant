"""
Test script to verify Gmail API setup and authentication.
This will test:
1. Authentication with credentials.json
2. Basic email fetching
3. Email classification (bot vs human)
4. Email actions (mark as read, move to folder, delete, forward, reply, star)
5. Historical email analysis for improved bot detection
6. Saving and loading learned weights
"""

import logging
from email_handler import GmailHandler
from datetime import datetime
import os

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_gmail_setup():
    """
    Test Gmail API setup and basic functionality.
    """
    try:
        # Create Gmail handler instance
        gmail = GmailHandler()
        
        # Test authentication
        logger.info("Testing Gmail authentication...")
        gmail.authenticate()
        logger.info("✓ Authentication successful!")
        
        # Check if we have saved weights
        weights_file = 'bot_weights.json'
        if os.path.exists(weights_file):
            logger.info("\nLoading previously learned weights...")
            if gmail.load_learned_weights(weights_file):
                logger.info("✓ Successfully loaded saved weights")
            else:
                logger.info("No valid weights file found, will analyze from scratch")
        
        # Analyze historical emails for better bot detection
        logger.info("\nAnalyzing historical emails to improve bot detection...")
        new_weights = gmail.analyze_historical_emails(months_back=24)
        logger.info("✓ Historical analysis complete. Bot detection weights updated.")
        
        # Save the learned weights
        logger.info("\nSaving learned weights...")
        if gmail.save_learned_weights(weights_file):
            logger.info("✓ Successfully saved weights for future use")
        
        # Fetch recent emails
        logger.info("\nFetching 5 most recent emails...")
        emails = gmail.fetch_recent_emails(max_results=5)
        
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
            is_bot, confidence = gmail.is_bot_generated(email.headers, email.body_text)
            
            # Get email summary
            summary = email.get_summary(max_length=100)
            
            # Print email details
            logger.info(f"Date: {date_str}")
            logger.info(f"From: {email.sender}")
            logger.info(f"To: {', '.join(email.recipients)}")
            logger.info(f"Subject: {subject}")
            logger.info(f"Summary: {summary}")
            logger.info(f"Classification: {'Bot' if is_bot else 'Human'} generated (confidence: {confidence:.2f})")
            logger.info("-" * 80)
            
            # Test email actions on the first email
            if email == emails[0]:
                logger.info("\nTesting email actions on first email...")
                
                # Test mark as read
                if gmail.mark_as_read(email.message_id):
                    logger.info("✓ Successfully marked email as read")
                
                # Test move to folder (using 'Important' as an example)
                if gmail.move_to_folder(email.message_id, 'Important'):
                    logger.info("✓ Successfully moved email to Important folder")
                
                # Test starring
                if gmail.star_email(email.message_id):
                    logger.info("✓ Successfully starred email")
                
                # Test forward (commented out for safety)
                # if gmail.forward_email(email.message_id, "test@example.com", "Please review this email"):
                #     logger.info("✓ Successfully forwarded email")
                
                # Test reply (commented out for safety)
                # if gmail.reply_to_email(email.message_id, "Thank you for your email. I will get back to you soon."):
                #     logger.info("✓ Successfully replied to email")
                
                # Test delete (commented out for safety)
                # if gmail.delete_email(email.message_id):
                #     logger.info("✓ Successfully moved email to trash")
                
                # Test unstar (commented out for safety)
                # if gmail.unstar_email(email.message_id):
                #     logger.info("✓ Successfully unstarred email")

    except FileNotFoundError:
        logger.error("❌ Error: credentials.json not found in the current directory!")
        logger.info("Please make sure you've downloaded credentials.json and placed it in the same directory as this script.")
    except Exception as e:
        logger.error(f"❌ Error during testing: {str(e)}")
        logger.info("Please check if your credentials are valid and you have internet connectivity.")

if __name__ == "__main__":
    logger.info("Starting Gmail API setup test...")
    test_gmail_setup()