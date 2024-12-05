#!/usr/bin/env python3
"""
Email Monitoring and Notification Application (Headless Version)

This headless application monitors an email inbox for unread emails and sends notifications
via various services like SMS, Voice Call, WhatsApp, Slack, Telegram, Discord, and Custom Webhooks.
It reads configurations from a config.ini file and logs activities to both the console and a log file.

Author: Seth Morrow
Date: Dec 2024
"""

import imaplib
import email
import time
import threading
import configparser
import os
from datetime import datetime
from email.header import decode_header
import logging
import signal
import sys

# Optional imports for notification services
from twilio.rest import Client  # For SMS, Voice Call, WhatsApp
from slack_sdk import WebClient  # For Slack notifications
from slack_sdk.errors import SlackApiError
import requests  # For Telegram, Discord, and Custom Webhooks

# Set the path for the configuration and log files
CONFIG_FILE_PATH = 'config.ini'
LOG_FILE_PATH = 'email_monitor.log'


def load_config(config_file=CONFIG_FILE_PATH):
    """
    Load configuration variables from a specified INI configuration file.

    Args:
        config_file (str): The path to the configuration INI file.

    Returns:
        configparser.ConfigParser: An instance containing the loaded configuration data.
    """
    config = configparser.ConfigParser()
    if not os.path.exists(config_file):
        # If the config file does not exist, create one with default values
        create_default_config(config_file)
    config.read(config_file)
    return config


def save_config(config, config_file=CONFIG_FILE_PATH):
    """
    Save configuration variables to a specified INI configuration file.

    Args:
        config (configparser.ConfigParser): The configuration data to save.
        config_file (str): The path to the configuration INI file.
    """
    with open(config_file, 'w') as file:
        config.write(file)


def create_default_config(config_file=CONFIG_FILE_PATH):
    """
    Create a default configuration file with placeholder values.

    Args:
        config_file (str): The path to the configuration INI file.
    """
    config = configparser.ConfigParser()

    config['Email'] = {
        'imap_server': 'imap.gmail.com',
        'imap_port': '993',
        'username': '',
        'password': '',
        'filter_emails': ''  # For email filtering
    }

    config['Settings'] = {
        'max_sms_length': '1600',
        'check_interval': '60'  # Check interval in seconds
    }

    # All notification methods
    config['Twilio'] = {
        'enabled': 'False',
        'account_sid': '',
        'auth_token': '',
        'from_number': '',
        'destination_number': ''
    }

    config['Voice'] = {
        'enabled': 'False',
        'account_sid': '',
        'auth_token': '',
        'from_number': '',
        'destination_number': ''
    }

    config['WhatsApp'] = {
        'enabled': 'False',
        'account_sid': '',
        'auth_token': '',
        'from_number': '',
        'to_number': ''
    }

    config['Slack'] = {
        'enabled': 'False',
        'token': '',
        'channel': ''
    }

    config['Telegram'] = {
        'enabled': 'False',
        'bot_token': '',
        'chat_id': ''
    }

    config['Discord'] = {
        'enabled': 'False',
        'webhook_url': ''
    }

    config['CustomWebhook'] = {
        'enabled': 'False',
        'webhook_url': ''
    }

    # Save the default configuration to the file
    with open(config_file, 'w') as file:
        config.write(file)


def setup_logging(log_file=LOG_FILE_PATH):
    """
    Set up logging to both console and a log file.

    Args:
        log_file (str): The path to the log file.
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Create formatter
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # File handler
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)


def connect_to_imap(server, port, username, password):
    """
    Establish a secure connection to the specified IMAP server and authenticate using provided credentials.

    Args:
        server (str): IMAP server address.
        port (int): IMAP server port.
        username (str): Email username.
        password (str): Email password.

    Returns:
        imaplib.IMAP4_SSL: An authenticated IMAP connection object.
    """
    try:
        imap = imaplib.IMAP4_SSL(server, port)
        imap.login(username, password)
        logging.info(f"Connected to IMAP server {server}:{port} as {username}.")
        return imap
    except Exception as e:
        logging.error(f"Failed to connect to IMAP server {server}:{port}: {e}")
        return None


def fetch_unread_emails(imap):
    """
    Retrieve unread emails from the inbox.

    Args:
        imap (imaplib.IMAP4_SSL): An authenticated IMAP connection object.

    Returns:
        list: A list of tuples containing email IDs and email message objects.
    """
    try:
        imap.select("inbox")  # Select the inbox folder
        status, messages = imap.search(None, 'UNSEEN')  # Search for unread messages
        if status != "OK":
            logging.warning("No unread emails found.")
            return []

        email_ids = messages[0].split()  # Get a list of email IDs
        if not email_ids:
            logging.info("No unread emails found.")
            return []

        # Convert email IDs to integers and sort in descending order (most recent first)
        email_ids = [int(eid) for eid in email_ids]
        email_ids.sort(reverse=True)
        # Take the 5 most recent email IDs
        email_ids = email_ids[:5]
        # Convert email IDs back to strings and encode to bytes
        email_ids = [str(eid).encode() for eid in email_ids]

        emails = []
        for email_id in email_ids:
            res, msg = imap.fetch(email_id, "(RFC822)")
            for response in msg:
                if isinstance(response, tuple):
                    # Parse the email message from bytes
                    msg = email.message_from_bytes(response[1])
                    emails.append((email_id, msg))  # Append the email ID and message object to the list
        return emails
    except Exception as e:
        logging.error(f"Failed to fetch emails: {e}")
        return []


def extract_email_body(msg):
    """
    Extract the plain text body from an email message object.

    Args:
        msg (email.message.EmailMessage): The email message object.

    Returns:
        str: The plain text body of the email.
    """
    try:
        if msg.is_multipart():
            # The email is multipart, so we need to iterate over its parts
            for part in msg.walk():
                # Check if the part is plain text and not an attachment
                if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                    # Decode the content from bytes to string using UTF-8 encoding
                    return part.get_payload(decode=True).decode("utf-8", errors='ignore')
            # If no plain text part is found, return an empty string
            return ""
        else:
            # The email is not multipart; decode the payload directly
            return msg.get_payload(decode=True).decode("utf-8", errors='ignore')
    except Exception as e:
        logging.error(f"Failed to extract email body: {e}")
        return ""


def mark_as_read(imap, email_id):
    """
    Mark an email as read on the IMAP server using the email ID.

    Args:
        imap (imaplib.IMAP4_SSL): An authenticated IMAP connection object.
        email_id (bytes): The email ID to mark as read.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        imap.store(email_id, '+FLAGS', '\\Seen')
        logging.info(f"Marked email {email_id.decode()} as read.")
        return True
    except Exception as e:
        logging.error(f"Failed to mark email {email_id.decode()} as read: {e}")
        return False


# Notification functions (implementations for each notification method)

def send_sms_via_twilio(account_sid, auth_token, from_number, to_number, body):
    """
    Send an SMS message using the Twilio API.

    Args:
        account_sid (str): Twilio account SID.
        auth_token (str): Twilio authentication token.
        from_number (str): Twilio phone number to send from.
        to_number (str): Recipient's phone number.
        body (str): Message body.

    Returns:
        str: Message SID if successful, None otherwise.
    """
    try:
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=body,
            from_=from_number,
            to=to_number
        )
        logging.info(f"Sent SMS to {to_number} with SID: {message.sid}")
        return message.sid
    except Exception as e:
        logging.error(f"Failed to send SMS to {to_number}: {e}")
        return None


def make_voice_call(account_sid, auth_token, from_number, to_number, message):
    """
    Make a voice call using the Twilio API and read out a message.

    Args:
        account_sid (str): Twilio account SID.
        auth_token (str): Twilio authentication token.
        from_number (str): Twilio phone number to call from.
        to_number (str): Recipient's phone number.
        message (str): Message to be read during the call.

    Returns:
        str: Call SID if successful, None otherwise.
    """
    try:
        client = Client(account_sid, auth_token)
        call = client.calls.create(
            twiml=f'<Response><Say>{message}</Say></Response>',
            from_=from_number,
            to=to_number
        )
        logging.info(f"Initiated voice call to {to_number} with SID: {call.sid}")
        return call.sid
    except Exception as e:
        logging.error(f"Failed to make voice call to {to_number}: {e}")
        return None


def send_whatsapp_message(account_sid, auth_token, from_number, to_number, body):
    """
    Send a WhatsApp message using the Twilio API.

    Args:
        account_sid (str): Twilio account SID.
        auth_token (str): Twilio authentication token.
        from_number (str): Twilio WhatsApp-enabled number (e.g., 'whatsapp:+14155238886').
        to_number (str): Recipient's WhatsApp number (e.g., 'whatsapp:+1234567890').
        body (str): Message body.

    Returns:
        str: Message SID if successful, None otherwise.
    """
    try:
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=body,
            from_=from_number,
            to=to_number
        )
        logging.info(f"Sent WhatsApp message to {to_number} with SID: {message.sid}")
        return message.sid
    except Exception as e:
        logging.error(f"Failed to send WhatsApp message to {to_number}: {e}")
        return None


def send_slack_message(token, channel, subject, body):
    """
    Send a message to a Slack channel using the Slack SDK.

    Args:
        token (str): Slack API token.
        channel (str): Slack channel name.
        subject (str): Subject of the message.
        body (str): Body of the message.

    Returns:
        str: Timestamp of the message if successful, None otherwise.
    """
    if not token or not channel:
        logging.warning("Slack token or channel not configured properly.")
        return None

    if not channel.startswith('#'):
        channel = f'#{channel}'

    try:
        client = WebClient(token=token)
        # Format the subject in bold by wrapping it with asterisks
        formatted_body = f"*{subject}*\n{body}"

        response = client.chat_postMessage(
            channel=channel,
            text=formatted_body,
            parse='full'  # Enable parsing of markup (e.g., bold, italics)
        )
        logging.info(f"Sent Slack message with timestamp: {response['ts']}")
        return response["ts"]
    except SlackApiError as e:
        logging.error(f"Failed to send Slack message: {e.response['error']}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error sending Slack message: {e}")
        return None


def send_telegram_message(bot_token, chat_id, subject, body):
    """
    Send a message to a Telegram chat using the Bot API via HTTP requests.

    Args:
        bot_token (str): Telegram bot token.
        chat_id (str): Telegram chat ID.
        subject (str): Subject of the message.
        body (str): Body of the message.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        message = f"*{subject}*\n{body}"
        url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
        params = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }
        response = requests.post(url, data=params)
        if response.status_code == 200:
            logging.info("Sent Telegram message.")
            return True
        else:
            logging.error(f"Failed to send Telegram message: {response.status_code} {response.text}")
            return False
    except Exception as e:
        logging.error(f"Failed to send Telegram message: {e}")
        return False


def send_discord_message(webhook_url, subject, body):
    """
    Send a message to a Discord channel using a webhook.

    Args:
        webhook_url (str): Discord webhook URL.
        subject (str): Subject of the message.
        body (str): Body of the message.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        data = {
            "content": f"**{subject}**\n{body}"
        }
        response = requests.post(webhook_url, json=data)
        if response.status_code in [200, 204]:
            logging.info("Sent Discord message.")
            return True
        else:
            logging.error(f"Failed to send Discord message: {response.status_code} {response.text}")
            return False
    except Exception as e:
        logging.error(f"Failed to send Discord message: {e}")
        return False


def send_custom_webhook(webhook_url, payload):
    """
    Send a custom payload to a specified webhook URL.

    Args:
        webhook_url (str): The webhook URL to send the payload to.
        payload (dict): The payload data to send.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code in [200, 201, 202]:
            logging.info("Sent custom webhook.")
            return True
        else:
            logging.error(f"Failed to send custom webhook: {response.status_code} {response.text}")
            return False
    except Exception as e:
        logging.error(f"Failed to send custom webhook: {e}")
        return False


class EmailMonitorApp:
    """
    The main application class for the Email Monitoring.
    """

    def __init__(self, config):
        """
        Initialize the EmailMonitorApp with configuration data.

        Args:
            config (configparser.ConfigParser): Configuration data loaded from config.ini.
        """
        self.config = config
        self.monitoring = False
        self.monitor_thread = None
        self.imap = None
        self.stop_event = threading.Event()

    def start(self):
        """
        Start the email monitoring process.
        """
        if self.monitoring:
            logging.warning("Monitoring is already running.")
            return

        # Validate that at least one notification method is enabled
        if not any([
            self.config.getboolean('Twilio', 'enabled', fallback=False),
            self.config.getboolean('Voice', 'enabled', fallback=False),
            self.config.getboolean('WhatsApp', 'enabled', fallback=False),
            self.config.getboolean('Slack', 'enabled', fallback=False),
            self.config.getboolean('Telegram', 'enabled', fallback=False),
            self.config.getboolean('Discord', 'enabled', fallback=False),
            self.config.getboolean('CustomWebhook', 'enabled', fallback=False)
        ]):
            logging.warning("No notification methods enabled. Please enable at least one method in config.ini.")
            return

        # Validate required Email settings
        email_section = self.config['Email']
        if not all([email_section.get('imap_server'), email_section.get('imap_port'),
                    email_section.get('username'), email_section.get('password')]):
            logging.warning("Incomplete Email configuration. Please ensure all fields are filled in config.ini.")
            return

        # Validate Check Interval
        try:
            check_interval = int(self.config['Settings'].get('check_interval', '60'))
            if check_interval <= 0:
                raise ValueError
        except ValueError:
            logging.warning("Invalid check_interval in config.ini. It must be a positive integer.")
            return

        self.monitoring = True
        self.stop_event.clear()
        logging.info("Starting email monitoring.")
        self.monitor_thread = threading.Thread(target=self.monitor_emails, daemon=True)
        self.monitor_thread.start()

    def stop(self):
        """
        Stop the email monitoring process.
        """
        if not self.monitoring:
            logging.warning("Monitoring is not running.")
            return

        self.monitoring = False
        self.stop_event.set()
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join()
        logging.info("Email monitoring stopped.")

    def monitor_emails(self):
        """
        Monitor the inbox for unread emails and send notifications as configured.
        """
        email_section = self.config['Email']
        settings_section = self.config['Settings']

        while not self.stop_event.is_set():
            try:
                # Retrieve Email credentials and settings
                IMAP_SERVER = email_section.get('imap_server')
                IMAP_PORT = int(email_section.get('imap_port'))
                EMAIL_USERNAME = email_section.get('username')
                EMAIL_PASSWORD = email_section.get('password')
                FILTER_EMAILS = [email.strip().lower() for email in email_section.get('filter_emails', '').split(',') if email.strip()]

                # Retrieve Check Interval
                CHECK_INTERVAL = int(settings_section.get('check_interval', '60'))

                # Retrieve Twilio SMS configuration
                TWILIO_SMS_ENABLED = self.config.getboolean('Twilio', 'enabled', fallback=False)
                TWILIO_SMS_ACCOUNT_SID = self.config.get('Twilio', 'account_sid', fallback='')
                TWILIO_SMS_AUTH_TOKEN = self.config.get('Twilio', 'auth_token', fallback='')
                TWILIO_SMS_FROM_NUMBER = self.config.get('Twilio', 'from_number', fallback='')
                TWILIO_SMS_DESTINATION_NUMBERS = [num.strip() for num in self.config.get('Twilio', 'destination_number', fallback='').split(',') if num.strip()]
                MAX_SMS_LENGTH = int(settings_section.get('max_sms_length', '1600'))

                # Retrieve Twilio Voice configuration
                VOICE_ENABLED = self.config.getboolean('Voice', 'enabled', fallback=False)
                VOICE_ACCOUNT_SID = self.config.get('Voice', 'account_sid', fallback='')
                VOICE_AUTH_TOKEN = self.config.get('Voice', 'auth_token', fallback='')
                VOICE_FROM_NUMBER = self.config.get('Voice', 'from_number', fallback='')
                VOICE_DESTINATION_NUMBERS = [num.strip() for num in self.config.get('Voice', 'destination_number', fallback='').split(',') if num.strip()]

                # Retrieve Twilio WhatsApp configuration
                WHATSAPP_ENABLED = self.config.getboolean('WhatsApp', 'enabled', fallback=False)
                WHATSAPP_ACCOUNT_SID = self.config.get('WhatsApp', 'account_sid', fallback='')
                WHATSAPP_AUTH_TOKEN = self.config.get('WhatsApp', 'auth_token', fallback='')
                WHATSAPP_FROM_NUMBER = self.config.get('WhatsApp', 'from_number', fallback='')
                WHATSAPP_TO_NUMBERS = [num.strip() for num in self.config.get('WhatsApp', 'to_number', fallback='').split(',') if num.strip()]

                # Retrieve Slack configuration
                SLACK_ENABLED = self.config.getboolean('Slack', 'enabled', fallback=False)
                SLACK_TOKEN = self.config.get('Slack', 'token', fallback='')
                SLACK_CHANNEL = self.config.get('Slack', 'channel', fallback='')

                # Retrieve Telegram configuration
                TELEGRAM_ENABLED = self.config.getboolean('Telegram', 'enabled', fallback=False)
                TELEGRAM_BOT_TOKEN = self.config.get('Telegram', 'bot_token', fallback='')
                TELEGRAM_CHAT_ID = self.config.get('Telegram', 'chat_id', fallback='')

                # Retrieve Discord configuration
                DISCORD_ENABLED = self.config.getboolean('Discord', 'enabled', fallback=False)
                DISCORD_WEBHOOK_URL = self.config.get('Discord', 'webhook_url', fallback='')

                # Retrieve Custom Webhook configuration
                CUSTOM_WEBHOOK_ENABLED = self.config.getboolean('CustomWebhook', 'enabled', fallback=False)
                CUSTOM_WEBHOOK_URL = self.config.get('CustomWebhook', 'webhook_url', fallback='')

                # Connect to the IMAP server
                imap = connect_to_imap(IMAP_SERVER, IMAP_PORT, EMAIL_USERNAME, EMAIL_PASSWORD)
                if not imap:
                    logging.warning(f"Failed to connect to IMAP server. Retrying in {CHECK_INTERVAL} seconds...")
                    time.sleep(CHECK_INTERVAL)
                    continue

                # Fetch unread emails
                unread_emails = fetch_unread_emails(imap)
                logging.info(f"Found {len(unread_emails)} unread email(s).")

                # Process each unread email
                for email_id, msg in unread_emails:
                    # Extract the sender's email address
                    sender = msg.get("From")
                    if sender:
                        sender_email = email.utils.parseaddr(sender)[1].lower()
                    else:
                        sender_email = ""

                    # Apply Email Filtering
                    if FILTER_EMAILS:
                        match = False
                        for filter_entry in FILTER_EMAILS:
                            if filter_entry.startswith('@'):
                                # Domain filter
                                domain = filter_entry[1:]
                                if sender_email.endswith(f"@{domain}"):
                                    match = True
                                    break
                            else:
                                # Specific email address filter
                                if sender_email == filter_entry:
                                    match = True
                                    break
                        if not match:
                            logging.info(f"Email from {sender_email} does not match filter criteria. Skipping.")
                            continue  # Skip to the next email

                    # Extract the subject and body from the email
                    # Decode the subject if necessary
                    subject, encoding = decode_header(msg.get("Subject"))[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8", errors='ignore')

                    # Extract the body of the email
                    body = extract_email_body(msg)
                    logging.info(f"Processing email from {sender_email} with subject: {subject}")

                    # Flag to track if any notification was sent successfully
                    success = False

                    # Construct the message for notifications
                    notification_message = f"{subject}: {body}"

                    # Send SMS via Twilio if enabled
                    if TWILIO_SMS_ENABLED:
                        sms_body = (notification_message[:MAX_SMS_LENGTH] + '...') if len(notification_message) > MAX_SMS_LENGTH else notification_message
                        for to_number in TWILIO_SMS_DESTINATION_NUMBERS:
                            sms_sid = send_sms_via_twilio(
                                account_sid=TWILIO_SMS_ACCOUNT_SID,
                                auth_token=TWILIO_SMS_AUTH_TOKEN,
                                from_number=TWILIO_SMS_FROM_NUMBER,
                                to_number=to_number,
                                body=sms_body
                            )
                            if sms_sid:
                                success = True

                    # Make Voice Call via Twilio if enabled
                    if VOICE_ENABLED:
                        for to_number in VOICE_DESTINATION_NUMBERS:
                            call_sid = make_voice_call(
                                account_sid=VOICE_ACCOUNT_SID,
                                auth_token=VOICE_AUTH_TOKEN,
                                from_number=VOICE_FROM_NUMBER,
                                to_number=to_number,
                                message=notification_message
                            )
                            if call_sid:
                                success = True

                    # Send WhatsApp message via Twilio if enabled
                    if WHATSAPP_ENABLED:
                        for to_number in WHATSAPP_TO_NUMBERS:
                            message_sid = send_whatsapp_message(
                                account_sid=WHATSAPP_ACCOUNT_SID,
                                auth_token=WHATSAPP_AUTH_TOKEN,
                                from_number=WHATSAPP_FROM_NUMBER,
                                to_number=to_number,
                                body=notification_message
                            )
                            if message_sid:
                                success = True

                    # Send Slack message if enabled
                    if SLACK_ENABLED:
                        slack_ts = send_slack_message(
                            token=SLACK_TOKEN,
                            channel=SLACK_CHANNEL,
                            subject=subject,
                            body=body
                        )
                        if slack_ts:
                            success = True

                    # Send Telegram message if enabled
                    if TELEGRAM_ENABLED:
                        telegram_success = send_telegram_message(
                            bot_token=TELEGRAM_BOT_TOKEN,
                            chat_id=TELEGRAM_CHAT_ID,
                            subject=subject,
                            body=body
                        )
                        if telegram_success:
                            success = True

                    # Send Discord message if enabled
                    if DISCORD_ENABLED:
                        discord_success = send_discord_message(
                            webhook_url=DISCORD_WEBHOOK_URL,
                            subject=subject,
                            body=body
                        )
                        if discord_success:
                            success = True

                    # Send Custom Webhook if enabled
                    if CUSTOM_WEBHOOK_ENABLED:
                        payload = {
                            'subject': subject,
                            'body': body
                        }
                        custom_webhook_success = send_custom_webhook(
                            webhook_url=CUSTOM_WEBHOOK_URL,
                            payload=payload
                        )
                        if custom_webhook_success:
                            success = True

                    # Mark the email as read if any notification was sent successfully
                    if success:
                        if mark_as_read(imap, email_id):
                            pass  # Already logged inside mark_as_read
                        else:
                            logging.warning(f"Failed to mark email {email_id.decode()} as read.")
                    else:
                        logging.info(f"No successful notifications sent for email {email_id.decode()}.")

            except Exception as e:
                logging.error(f"An error occurred during email monitoring: {e}")
            finally:
                # Ensure the IMAP connection is properly closed
                if imap:
                    try:
                        imap.logout()
                        logging.info("Logged out from IMAP server.")
                    except Exception as e:
                        logging.error(f"Error while logging out from IMAP: {e}")
                # Wait before checking for new emails again based on check interval
                if not self.stop_event.is_set():
                    logging.info(f"Waiting for {CHECK_INTERVAL} seconds before the next check.")
                    time.sleep(CHECK_INTERVAL)


def signal_handler(sig, frame, app):
    """
    Handle termination signals to gracefully shut down the application.

    Args:
        sig (int): Signal number.
        frame (object): Current stack frame.
        app (EmailMonitorApp): Instance of the EmailMonitorApp.
    """
    logging.info(f"Received signal {sig}. Shutting down gracefully...")
    app.stop()
    sys.exit(0)


def main():
    """
    The main function to run the Email Monitoring application.
    """
    # Set up logging
    setup_logging()

    # Load configuration
    config = load_config()

    # Initialize the application
    app = EmailMonitorApp(config)

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, lambda sig, frame: signal_handler(sig, frame, app))
    signal.signal(signal.SIGTERM, lambda sig, frame: signal_handler(sig, frame, app))

    # Start monitoring
    app.start()

    # Keep the main thread alive while monitoring is active
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received. Exiting...")
        app.stop()
        sys.exit(0)


if __name__ == '__main__':
    main()
