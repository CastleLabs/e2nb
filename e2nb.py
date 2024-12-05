#!/usr/bin/env python3
"""
Email Monitoring and Notification Application with GUI and Configuration File

This application monitors an email inbox for unread emails and sends notifications
via various services like SMS, Voice Call, WhatsApp, Slack, Telegram, Discord,
and Custom Webhooks. It includes a graphical user interface (GUI) built with Tkinter
for easy configuration and control.

The application reads configurations from a config.ini file and can save updates
back to the file when settings are changed through the GUI.

Author: Seth Morrow
Date: Dec 2024
"""

import imaplib
import email
import time
import threading
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import scrolledtext
from tkinter import Menu
import tkinter.font as tkFont
from email.header import decode_header
import configparser  # For reading and writing configuration files
import os  # For checking if the config file exists
from datetime import datetime

# Optional imports for notification services
from twilio.rest import Client  # For SMS, Voice Call, WhatsApp
from slack_sdk import WebClient  # For Slack notifications
from slack_sdk.errors import SlackApiError
import requests  # For Telegram, Discord, and Custom Webhooks

# Set the path for the configuration file
CONFIG_FILE_PATH = 'config.ini'


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
        return imap
    except Exception as e:
        print(f"Failed to connect to IMAP server {server}:{port}: {e}")
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
            print("No unread emails found.")
            return []

        email_ids = messages[0].split()  # Get a list of email IDs
        if not email_ids:
            print("No unread emails found.")
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
        print(f"Failed to fetch emails: {e}")
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
                    return part.get_payload(decode=True).decode("utf-8")
            # If no plain text part is found, return an empty string
            return ""
        else:
            # The email is not multipart; decode the payload directly
            return msg.get_payload(decode=True).decode("utf-8")
    except Exception as e:
        print(f"Failed to extract email body: {e}")
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
        return True
    except Exception as e:
        print(f"Failed to mark email as read: {e}")
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
        return message.sid
    except Exception as e:
        print(f"Failed to send SMS to {to_number}: {e}")
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
        return call.sid
    except Exception as e:
        print(f"Failed to make voice call to {to_number}: {e}")
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
        return message.sid
    except Exception as e:
        print(f"Failed to send WhatsApp message to {to_number}: {e}")
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
        print("Slack token or channel not configured properly")
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
        return response["ts"]
    except SlackApiError as e:
        print(f"Failed to send Slack message: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error sending Slack message: {e}")
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
            return True
        else:
            print(f"Failed to send Telegram message: {response.status_code} {response.text}")
            return False
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")
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
            return True
        else:
            print(f"Failed to send Discord message: {response.status_code} {response.text}")
            return False
    except Exception as e:
        print(f"Failed to send Discord message: {e}")
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
            return True
        else:
            print(f"Failed to send custom webhook: {response.status_code} {response.text}")
            return False
    except Exception as e:
        print(f"Failed to send custom webhook: {e}")
        return False


class EmailMonitorApp:
    """
    The main application class for the Email Monitoring GUI.

    Attributes:
        root (tk.Tk): The main Tkinter window.
        config (configparser.ConfigParser): Configuration data loaded from config.ini.
        monitoring (bool): Flag indicating if monitoring is active.
    """

    def __init__(self, root):
        """
        Initialize the EmailMonitorApp with the main Tkinter window.

        Args:
            root (tk.Tk): The main Tkinter window.
        """
        self.root = root
        self.root.title("Email to Notification Blaster")
        self.config = load_config()
        self.monitoring = False

        # Apply a modern theme
        style = ttk.Style()
        style.theme_use('clam')

        # Set custom fonts
        self.default_font = tkFont.nametofont("TkDefaultFont")
        self.default_font.configure(size=10)

        # Set window icon (optional, provide your own icon file)
        # self.root.iconbitmap('icon.ico')

        # Create the menu bar
        self.create_menu()

        # Create and layout all widgets
        self.create_widgets()

    def create_menu(self):
        """
        Create the menu bar for the application.
        """
        menubar = Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = Menu(menubar, tearoff=False)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save Settings", command=self.save_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Help menu
        help_menu = Menu(menubar, tearoff=False)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

    def show_about(self):
        """
        Display the About dialog.
        """
        messagebox.showinfo("About", "Email Notification Blaster\nVersion 0.0.1\nAuthor: Seth Morrow")

    def create_widgets(self):
        """
        Create and layout all GUI widgets within the application window.
        """
        # Create a notebook to hold tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Create frames for each tab
        self.email_frame = ttk.Frame(self.notebook)
        self.settings_frame = ttk.Frame(self.notebook)
        self.notification_frame = ttk.Frame(self.notebook)
        self.twilio_sms_frame = ttk.Frame(self.notebook)
        self.twilio_voice_frame = ttk.Frame(self.notebook)
        self.twilio_whatsapp_frame = ttk.Frame(self.notebook)
        self.slack_frame = ttk.Frame(self.notebook)
        self.telegram_frame = ttk.Frame(self.notebook)
        self.discord_frame = ttk.Frame(self.notebook)
        self.custom_webhook_frame = ttk.Frame(self.notebook)
        self.log_frame = ttk.Frame(self.notebook)

        # Add tabs to the notebook
        self.notebook.add(self.email_frame, text="Email Settings")
        self.notebook.add(self.settings_frame, text="Settings")
        self.notebook.add(self.notification_frame, text="Notification Methods")
        self.notebook.add(self.twilio_sms_frame, text="Twilio SMS")
        self.notebook.add(self.twilio_voice_frame, text="Twilio Voice")
        self.notebook.add(self.twilio_whatsapp_frame, text="Twilio WhatsApp")
        self.notebook.add(self.slack_frame, text="Slack")
        self.notebook.add(self.telegram_frame, text="Telegram")
        self.notebook.add(self.discord_frame, text="Discord")
        self.notebook.add(self.custom_webhook_frame, text="Custom Webhook")
        self.notebook.add(self.log_frame, text="Logs")

        # Email Configuration Tab
        self.create_email_tab()

        # Settings Tab
        self.create_settings_tab()

        # Notification Methods Tab
        self.create_notification_methods_tab()

        # Twilio SMS Configuration Tab
        self.create_twilio_sms_tab()

        # Twilio Voice Configuration Tab
        self.create_twilio_voice_tab()

        # Twilio WhatsApp Configuration Tab
        self.create_twilio_whatsapp_tab()

        # Slack Configuration Tab
        self.create_slack_tab()

        # Telegram Configuration Tab
        self.create_telegram_tab()

        # Discord Configuration Tab
        self.create_discord_tab()

        # Custom Webhook Configuration Tab
        self.create_custom_webhook_tab()

        # Logs Tab
        self.create_logs_tab()

        # Control Buttons
        self.create_control_buttons()

    def create_email_tab(self):
        """
        Create widgets for the Email configuration tab.
        """
        frame = ttk.Frame(self.email_frame, padding="10 10 10 10")
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="IMAP Server:").grid(column=0, row=0, sticky="W", pady=5)
        self.imap_server_entry = ttk.Entry(frame, width=30)
        self.imap_server_entry.grid(column=1, row=0, pady=5, sticky="EW")
        self.imap_server_entry.insert(0, self.config.get('Email', 'imap_server', fallback=''))

        ttk.Label(frame, text="Port:").grid(column=0, row=1, sticky="W", pady=5)
        self.imap_port_entry = ttk.Entry(frame, width=10)
        self.imap_port_entry.grid(column=1, row=1, pady=5, sticky="EW")
        self.imap_port_entry.insert(0, self.config.get('Email', 'imap_port', fallback='993'))

        ttk.Label(frame, text="Username:").grid(column=0, row=2, sticky="W", pady=5)
        self.username_entry = ttk.Entry(frame, width=30)
        self.username_entry.grid(column=1, row=2, pady=5, sticky="EW")
        self.username_entry.insert(0, self.config.get('Email', 'username', fallback=''))

        ttk.Label(frame, text="Password:").grid(column=0, row=3, sticky="W", pady=5)
        self.password_entry = ttk.Entry(frame, width=30, show="*")
        self.password_entry.grid(column=1, row=3, pady=5, sticky="EW")
        self.password_entry.insert(0, self.config.get('Email', 'password', fallback=''))

        # Email Filtering Field
        ttk.Label(frame, text="Filter Emails (@domain or email):").grid(column=0, row=4, sticky="W", pady=5)
        self.filter_emails_entry = ttk.Entry(frame, width=50)
        self.filter_emails_entry.grid(column=1, row=4, pady=5, sticky="EW")
        self.filter_emails_entry.insert(0, self.config.get('Email', 'filter_emails', fallback=''))

        ttk.Label(frame, text="(Separate multiple entries with commas)").grid(column=0, row=5, columnspan=2, pady=5, sticky="W")

    def create_settings_tab(self):
        """
        Create widgets for the Settings tab.
        """
        frame = ttk.Frame(self.settings_frame, padding="10 10 10 10")
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Max SMS Length:").grid(column=0, row=0, sticky="W", pady=5)
        self.max_sms_length_entry = ttk.Entry(frame, width=10)
        self.max_sms_length_entry.grid(column=1, row=0, pady=5, sticky="EW")
        self.max_sms_length_entry.insert(0, self.config.get('Settings', 'max_sms_length', fallback='1600'))

        # Check Interval Field
        ttk.Label(frame, text="Check Interval (seconds):").grid(column=0, row=1, sticky="W", pady=5)
        self.check_interval_entry = ttk.Entry(frame, width=10)
        self.check_interval_entry.grid(column=1, row=1, pady=5, sticky="EW")
        self.check_interval_entry.insert(0, self.config.get('Settings', 'check_interval', fallback='60'))

    def create_notification_methods_tab(self):
        """
        Create widgets for the Notification Methods tab.
        """
        frame = ttk.Frame(self.notification_frame, padding="10 10 10 10")
        frame.pack(fill="both", expand=True)

        # Define BooleanVars for each notification method
        self.twilio_sms_var = tk.BooleanVar(value=self.config.getboolean('Twilio', 'enabled', fallback=False))
        self.voice_var = tk.BooleanVar(value=self.config.getboolean('Voice', 'enabled', fallback=False))
        self.whatsapp_var = tk.BooleanVar(value=self.config.getboolean('WhatsApp', 'enabled', fallback=False))
        self.slack_var = tk.BooleanVar(value=self.config.getboolean('Slack', 'enabled', fallback=False))
        self.telegram_var = tk.BooleanVar(value=self.config.getboolean('Telegram', 'enabled', fallback=False))
        self.discord_var = tk.BooleanVar(value=self.config.getboolean('Discord', 'enabled', fallback=False))
        self.custom_webhook_var = tk.BooleanVar(value=self.config.getboolean('CustomWebhook', 'enabled', fallback=False))

        # Add Checkbuttons for each notification method
        ttk.Checkbutton(frame, text="SMS via Twilio", variable=self.twilio_sms_var).grid(column=0, row=0, sticky="W", pady=5)
        ttk.Checkbutton(frame, text="Voice Call via Twilio", variable=self.voice_var).grid(column=1, row=0, sticky="W", pady=5)
        ttk.Checkbutton(frame, text="WhatsApp via Twilio", variable=self.whatsapp_var).grid(column=0, row=1, sticky="W", pady=5)
        ttk.Checkbutton(frame, text="Slack", variable=self.slack_var).grid(column=1, row=1, sticky="W", pady=5)
        ttk.Checkbutton(frame, text="Telegram", variable=self.telegram_var).grid(column=0, row=2, sticky="W", pady=5)
        ttk.Checkbutton(frame, text="Discord", variable=self.discord_var).grid(column=1, row=2, sticky="W", pady=5)
        ttk.Checkbutton(frame, text="Custom Webhook", variable=self.custom_webhook_var).grid(column=0, row=3, sticky="W", pady=5)

    def create_twilio_sms_tab(self):
        """
        Create widgets for the Twilio SMS configuration tab.
        """
        frame = ttk.Frame(self.twilio_sms_frame, padding="10 10 10 10")
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Account SID:").grid(column=0, row=0, sticky="W", pady=5)
        self.twilio_sms_sid_entry = ttk.Entry(frame, width=30)
        self.twilio_sms_sid_entry.grid(column=1, row=0, pady=5, sticky="EW")
        self.twilio_sms_sid_entry.insert(0, self.config.get('Twilio', 'account_sid', fallback=''))

        ttk.Label(frame, text="Auth Token:").grid(column=0, row=1, sticky="W", pady=5)
        self.twilio_sms_token_entry = ttk.Entry(frame, width=30, show="*")
        self.twilio_sms_token_entry.grid(column=1, row=1, pady=5, sticky="EW")
        self.twilio_sms_token_entry.insert(0, self.config.get('Twilio', 'auth_token', fallback=''))

        ttk.Label(frame, text="From Number:").grid(column=0, row=2, sticky="W", pady=5)
        self.twilio_sms_from_entry = ttk.Entry(frame, width=30)
        self.twilio_sms_from_entry.grid(column=1, row=2, pady=5, sticky="EW")
        self.twilio_sms_from_entry.insert(0, self.config.get('Twilio', 'from_number', fallback=''))

        ttk.Label(frame, text="Destination Number(s):").grid(column=0, row=3, sticky="W", pady=5)
        self.twilio_sms_to_entry = ttk.Entry(frame, width=30)
        self.twilio_sms_to_entry.grid(column=1, row=3, pady=5, sticky="EW")
        dest_numbers = self.config.get('Twilio', 'destination_number', fallback='')
        self.twilio_sms_to_entry.insert(0, dest_numbers)
        ttk.Label(frame, text="(Separate multiple numbers with commas)").grid(column=0, row=4, columnspan=2, pady=5, sticky="W")

    def create_twilio_voice_tab(self):
        """
        Create widgets for the Twilio Voice configuration tab.
        """
        frame = ttk.Frame(self.twilio_voice_frame, padding="10 10 10 10")
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Account SID:").grid(column=0, row=0, sticky="W", pady=5)
        self.twilio_voice_sid_entry = ttk.Entry(frame, width=30)
        self.twilio_voice_sid_entry.grid(column=1, row=0, pady=5, sticky="EW")
        self.twilio_voice_sid_entry.insert(0, self.config.get('Voice', 'account_sid', fallback=''))

        ttk.Label(frame, text="Auth Token:").grid(column=0, row=1, sticky="W", pady=5)
        self.twilio_voice_token_entry = ttk.Entry(frame, width=30, show="*")
        self.twilio_voice_token_entry.grid(column=1, row=1, pady=5, sticky="EW")
        self.twilio_voice_token_entry.insert(0, self.config.get('Voice', 'auth_token', fallback=''))

        ttk.Label(frame, text="From Number:").grid(column=0, row=2, sticky="W", pady=5)
        self.twilio_voice_from_entry = ttk.Entry(frame, width=30)
        self.twilio_voice_from_entry.grid(column=1, row=2, pady=5, sticky="EW")
        self.twilio_voice_from_entry.insert(0, self.config.get('Voice', 'from_number', fallback=''))

        ttk.Label(frame, text="Destination Number(s):").grid(column=0, row=3, sticky="W", pady=5)
        self.twilio_voice_to_entry = ttk.Entry(frame, width=30)
        self.twilio_voice_to_entry.grid(column=1, row=3, pady=5, sticky="EW")
        dest_numbers = self.config.get('Voice', 'destination_number', fallback='')
        self.twilio_voice_to_entry.insert(0, dest_numbers)
        ttk.Label(frame, text="(Separate multiple numbers with commas)").grid(column=0, row=4, columnspan=2, pady=5, sticky="W")

    def create_twilio_whatsapp_tab(self):
        """
        Create widgets for the Twilio WhatsApp configuration tab.
        """
        frame = ttk.Frame(self.twilio_whatsapp_frame, padding="10 10 10 10")
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Account SID:").grid(column=0, row=0, sticky="W", pady=5)
        self.twilio_whatsapp_sid_entry = ttk.Entry(frame, width=30)
        self.twilio_whatsapp_sid_entry.grid(column=1, row=0, pady=5, sticky="EW")
        self.twilio_whatsapp_sid_entry.insert(0, self.config.get('WhatsApp', 'account_sid', fallback=''))

        ttk.Label(frame, text="Auth Token:").grid(column=0, row=1, sticky="W", pady=5)
        self.twilio_whatsapp_token_entry = ttk.Entry(frame, width=30, show="*")
        self.twilio_whatsapp_token_entry.grid(column=1, row=1, pady=5, sticky="EW")
        self.twilio_whatsapp_token_entry.insert(0, self.config.get('WhatsApp', 'auth_token', fallback=''))

        ttk.Label(frame, text="From Number:").grid(column=0, row=2, sticky="W", pady=5)
        self.twilio_whatsapp_from_entry = ttk.Entry(frame, width=30)
        self.twilio_whatsapp_from_entry.grid(column=1, row=2, pady=5, sticky="EW")
        self.twilio_whatsapp_from_entry.insert(0, self.config.get('WhatsApp', 'from_number', fallback=''))

        ttk.Label(frame, text="To Number(s):").grid(column=0, row=3, sticky="W", pady=5)
        self.twilio_whatsapp_to_entry = ttk.Entry(frame, width=30)
        self.twilio_whatsapp_to_entry.grid(column=1, row=3, pady=5, sticky="EW")
        dest_numbers = self.config.get('WhatsApp', 'to_number', fallback='')
        self.twilio_whatsapp_to_entry.insert(0, dest_numbers)
        ttk.Label(frame, text="(Separate multiple numbers with commas)").grid(column=0, row=4, columnspan=2, pady=5, sticky="W")

    def create_slack_tab(self):
        """
        Create widgets for the Slack configuration tab.
        """
        frame = ttk.Frame(self.slack_frame, padding="10 10 10 10")
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Slack Token:").grid(column=0, row=0, sticky="W", pady=5)
        self.slack_token_entry = ttk.Entry(frame, width=50, show="*")
        self.slack_token_entry.grid(column=1, row=0, pady=5, sticky="EW")
        self.slack_token_entry.insert(0, self.config.get('Slack', 'token', fallback=''))

        ttk.Label(frame, text="Channel Name:").grid(column=0, row=1, sticky="W", pady=5)
        self.slack_channel_entry = ttk.Entry(frame, width=30)
        self.slack_channel_entry.grid(column=1, row=1, pady=5, sticky="EW")
        self.slack_channel_entry.insert(0, self.config.get('Slack', 'channel', fallback=''))

    def create_telegram_tab(self):
        """
        Create widgets for the Telegram configuration tab.
        """
        frame = ttk.Frame(self.telegram_frame, padding="10 10 10 10")
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Bot Token:").grid(column=0, row=0, sticky="W", pady=5)
        self.telegram_bot_token_entry = ttk.Entry(frame, width=50, show="*")
        self.telegram_bot_token_entry.grid(column=1, row=0, pady=5, sticky="EW")
        self.telegram_bot_token_entry.insert(0, self.config.get('Telegram', 'bot_token', fallback=''))

        ttk.Label(frame, text="Chat ID:").grid(column=0, row=1, sticky="W", pady=5)
        self.telegram_chat_id_entry = ttk.Entry(frame, width=30)
        self.telegram_chat_id_entry.grid(column=1, row=1, pady=5, sticky="EW")
        self.telegram_chat_id_entry.insert(0, self.config.get('Telegram', 'chat_id', fallback=''))

    def create_discord_tab(self):
        """
        Create widgets for the Discord configuration tab.
        """
        frame = ttk.Frame(self.discord_frame, padding="10 10 10 10")
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Webhook URL:").grid(column=0, row=0, sticky="W", pady=5)
        self.discord_webhook_entry = ttk.Entry(frame, width=70)
        self.discord_webhook_entry.grid(column=1, row=0, pady=5, sticky="EW")
        self.discord_webhook_entry.insert(0, self.config.get('Discord', 'webhook_url', fallback=''))

    def create_custom_webhook_tab(self):
        """
        Create widgets for the Custom Webhook configuration tab.
        """
        frame = ttk.Frame(self.custom_webhook_frame, padding="10 10 10 10")
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Webhook URL:").grid(column=0, row=0, sticky="W", pady=5)
        self.custom_webhook_entry = ttk.Entry(frame, width=70)
        self.custom_webhook_entry.grid(column=1, row=0, pady=5, sticky="EW")
        self.custom_webhook_entry.insert(0, self.config.get('CustomWebhook', 'webhook_url', fallback=''))

    def create_logs_tab(self):
        """
        Create widgets for the Logs tab.
        """
        frame = ttk.Frame(self.log_frame, padding="10 10 10 10")
        frame.pack(fill="both", expand=True)

        self.log_text = scrolledtext.ScrolledText(frame, height=15, state='disabled')
        self.log_text.pack(fill="both", expand=True)

    def create_control_buttons(self):
        """
        Create control buttons and place them at the bottom of the window.
        """
        button_frame = ttk.Frame(self.root, padding="10 10 10 10")
        button_frame.pack(fill="x", padx=5, pady=5)

        self.start_button = ttk.Button(button_frame, text="Start Monitoring", command=self.start_monitoring)
        self.start_button.pack(side="left", padx=5)

        self.stop_button = ttk.Button(button_frame, text="Stop Monitoring", command=self.stop_monitoring, state="disabled")
        self.stop_button.pack(side="left", padx=5)

        self.save_button = ttk.Button(button_frame, text="Save Settings", command=self.save_settings)
        self.save_button.pack(side="left", padx=5)

    def save_settings(self):
        """
        Save the current settings from the GUI into the config.ini file.
        """
        # Update the configuration object with values from the GUI
        self.config['Email']['imap_server'] = self.imap_server_entry.get()
        self.config['Email']['imap_port'] = self.imap_port_entry.get()
        self.config['Email']['username'] = self.username_entry.get()
        self.config['Email']['password'] = self.password_entry.get()
        self.config['Email']['filter_emails'] = self.filter_emails_entry.get()  # Save email filters

        self.config['Settings']['max_sms_length'] = self.max_sms_length_entry.get()
        self.config['Settings']['check_interval'] = self.check_interval_entry.get()  # Save check interval

        self.config['Twilio']['enabled'] = str(self.twilio_sms_var.get())
        self.config['Twilio']['account_sid'] = self.twilio_sms_sid_entry.get()
        self.config['Twilio']['auth_token'] = self.twilio_sms_token_entry.get()
        self.config['Twilio']['from_number'] = self.twilio_sms_from_entry.get()
        self.config['Twilio']['destination_number'] = self.twilio_sms_to_entry.get()

        self.config['Voice']['enabled'] = str(self.voice_var.get())
        self.config['Voice']['account_sid'] = self.twilio_voice_sid_entry.get()
        self.config['Voice']['auth_token'] = self.twilio_voice_token_entry.get()
        self.config['Voice']['from_number'] = self.twilio_voice_from_entry.get()
        self.config['Voice']['destination_number'] = self.twilio_voice_to_entry.get()

        self.config['WhatsApp']['enabled'] = str(self.whatsapp_var.get())
        self.config['WhatsApp']['account_sid'] = self.twilio_whatsapp_sid_entry.get()
        self.config['WhatsApp']['auth_token'] = self.twilio_whatsapp_token_entry.get()
        self.config['WhatsApp']['from_number'] = self.twilio_whatsapp_from_entry.get()
        self.config['WhatsApp']['to_number'] = self.twilio_whatsapp_to_entry.get()

        self.config['Slack']['enabled'] = str(self.slack_var.get())
        self.config['Slack']['token'] = self.slack_token_entry.get()
        self.config['Slack']['channel'] = self.slack_channel_entry.get()

        self.config['Telegram']['enabled'] = str(self.telegram_var.get())
        self.config['Telegram']['bot_token'] = self.telegram_bot_token_entry.get()
        self.config['Telegram']['chat_id'] = self.telegram_chat_id_entry.get()

        self.config['Discord']['enabled'] = str(self.discord_var.get())
        self.config['Discord']['webhook_url'] = self.discord_webhook_entry.get()

        self.config['CustomWebhook']['enabled'] = str(self.custom_webhook_var.get())
        self.config['CustomWebhook']['webhook_url'] = self.custom_webhook_entry.get()

        # Save the updated configuration to the file
        save_config(self.config)
        messagebox.showinfo("Settings Saved", "Settings have been saved to config.ini.")
        self.log("Settings saved to config.ini.")

    def start_monitoring(self):
        """
        Start the email monitoring process in a separate thread.
        """
        # Validate that at least one notification method is selected
        if not any([
            self.twilio_sms_var.get(), self.voice_var.get(),
            self.whatsapp_var.get(), self.slack_var.get(),
            self.telegram_var.get(), self.discord_var.get(),
            self.custom_webhook_var.get()
        ]):
            messagebox.showwarning("No Notification Method", "Please select at least one notification method.")
            return

        # Validate required fields (e.g., Email credentials)
        if not self.imap_server_entry.get() or not self.imap_port_entry.get() or not self.username_entry.get() or not self.password_entry.get():
            messagebox.showwarning("Missing Credentials", "Please enter your email server settings and credentials.")
            return

        # Validate Check Interval
        try:
            check_interval = int(self.check_interval_entry.get())
            if check_interval <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid Check Interval", "Please enter a valid positive integer for the check interval.")
            return

        # Disable the start button and enable the stop button
        self.monitoring = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.log("Monitoring started.")

        # Start the monitoring in a separate thread to keep the GUI responsive
        self.monitor_thread = threading.Thread(target=self.monitor_emails)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop_monitoring(self):
        """
        Stop the email monitoring process.
        """
        self.monitoring = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.log("Monitoring stopped.")

    def log(self, message):
        """
        Append a message to the log text area.

        Args:
            message (str): The message to log.
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted_message = f"[{timestamp}] {message}\n"
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.configure(state='disabled')
        self.log_text.see(tk.END)

    def monitor_emails(self):
        """
        Monitor the inbox for unread emails and send notifications as configured.
        """
        while self.monitoring:
            imap = None
            try:
                # Retrieve Email credentials and settings from GUI inputs
                IMAP_SERVER = self.imap_server_entry.get()
                IMAP_PORT = int(self.imap_port_entry.get())
                EMAIL_USERNAME = self.username_entry.get()
                EMAIL_PASSWORD = self.password_entry.get()
                FILTER_EMAILS = [email.strip().lower() for email in self.filter_emails_entry.get().split(',') if email.strip()]

                # Retrieve Check Interval
                CHECK_INTERVAL = int(self.check_interval_entry.get())

                # Retrieve Twilio SMS configuration
                TWILIO_SMS_ENABLED = self.twilio_sms_var.get()
                TWILIO_SMS_ACCOUNT_SID = self.twilio_sms_sid_entry.get()
                TWILIO_SMS_AUTH_TOKEN = self.twilio_sms_token_entry.get()
                TWILIO_SMS_FROM_NUMBER = self.twilio_sms_from_entry.get()
                TWILIO_SMS_TO_NUMBERS = [num.strip() for num in self.twilio_sms_to_entry.get().split(',') if num.strip()]
                MAX_SMS_LENGTH = int(self.max_sms_length_entry.get())

                # Retrieve Twilio Voice configuration
                VOICE_ENABLED = self.voice_var.get()
                VOICE_ACCOUNT_SID = self.twilio_voice_sid_entry.get()
                VOICE_AUTH_TOKEN = self.twilio_voice_token_entry.get()
                VOICE_FROM_NUMBER = self.twilio_voice_from_entry.get()
                VOICE_TO_NUMBERS = [num.strip() for num in self.twilio_voice_to_entry.get().split(',') if num.strip()]

                # Retrieve Twilio WhatsApp configuration
                WHATSAPP_ENABLED = self.whatsapp_var.get()
                WHATSAPP_ACCOUNT_SID = self.twilio_whatsapp_sid_entry.get()
                WHATSAPP_AUTH_TOKEN = self.twilio_whatsapp_token_entry.get()
                WHATSAPP_FROM_NUMBER = self.twilio_whatsapp_from_entry.get()
                WHATSAPP_TO_NUMBERS = [num.strip() for num in self.twilio_whatsapp_to_entry.get().split(',') if num.strip()]

                # Retrieve Slack configuration
                SLACK_ENABLED = self.slack_var.get()
                SLACK_TOKEN = self.slack_token_entry.get()
                SLACK_CHANNEL = self.slack_channel_entry.get()

                # Retrieve Telegram configuration
                TELEGRAM_ENABLED = self.telegram_var.get()
                TELEGRAM_BOT_TOKEN = self.telegram_bot_token_entry.get()
                TELEGRAM_CHAT_ID = self.telegram_chat_id_entry.get()

                # Retrieve Discord configuration
                DISCORD_ENABLED = self.discord_var.get()
                DISCORD_WEBHOOK_URL = self.discord_webhook_entry.get()

                # Retrieve Custom Webhook configuration
                CUSTOM_WEBHOOK_ENABLED = self.custom_webhook_var.get()
                CUSTOM_WEBHOOK_URL = self.custom_webhook_entry.get()

                # Connect to the specified IMAP server
                imap = connect_to_imap(IMAP_SERVER, IMAP_PORT, EMAIL_USERNAME, EMAIL_PASSWORD)
                if not imap:
                    self.log(f"Failed to connect to IMAP server {IMAP_SERVER}:{IMAP_PORT}. Retrying in {CHECK_INTERVAL} seconds...")
                    time.sleep(CHECK_INTERVAL)
                    continue

                # Fetch unread emails from the inbox
                unread_emails = fetch_unread_emails(imap)
                self.log(f"Found {len(unread_emails)} unread emails.")

                # Process each unread email individually
                for email_id, msg in unread_emails:
                    # Extract the sender's email address
                    sender = msg.get("From")
                    if sender:
                        # Parse the sender's email address
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
                            self.log(f"Email from {sender_email} does not match filter criteria. Skipping.")
                            continue  # Skip to the next email

                    # Extract the subject and body from the email
                    # Decode the subject if necessary
                    subject, encoding = decode_header(msg.get("Subject"))[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")

                    # Extract the body of the email
                    body = extract_email_body(msg)
                    self.log(f"Processing email from {sender_email} with subject: {subject}")

                    # Flag to track if any notification was sent successfully
                    success = False

                    # Construct the message for notifications
                    notification_message = f"{subject}: {body}"

                    # Send SMS via Twilio if enabled
                    if TWILIO_SMS_ENABLED:
                        sms_body = notification_message[:MAX_SMS_LENGTH] if len(notification_message) > MAX_SMS_LENGTH else notification_message
                        for to_number in TWILIO_SMS_TO_NUMBERS:
                            sms_sid = send_sms_via_twilio(
                                account_sid=TWILIO_SMS_ACCOUNT_SID,
                                auth_token=TWILIO_SMS_AUTH_TOKEN,
                                from_number=TWILIO_SMS_FROM_NUMBER,
                                to_number=to_number,
                                body=sms_body
                            )
                            if sms_sid:
                                self.log(f"Sent SMS to {to_number} with SID: {sms_sid}")
                                success = True
                            else:
                                self.log(f"Failed to send SMS to {to_number}")

                    # Make Voice Call via Twilio if enabled
                    if VOICE_ENABLED:
                        for to_number in VOICE_TO_NUMBERS:
                            call_sid = make_voice_call(
                                account_sid=VOICE_ACCOUNT_SID,
                                auth_token=VOICE_AUTH_TOKEN,
                                from_number=VOICE_FROM_NUMBER,
                                to_number=to_number,
                                message=notification_message
                            )
                            if call_sid:
                                self.log(f"Initiated voice call to {to_number} with SID: {call_sid}")
                                success = True
                            else:
                                self.log(f"Failed to initiate voice call to {to_number}")

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
                                self.log(f"Sent WhatsApp message to {to_number} with SID: {message_sid}")
                                success = True
                            else:
                                self.log(f"Failed to send WhatsApp message to {to_number}")

                    # Send Slack message if enabled
                    if SLACK_ENABLED:
                        slack_ts = send_slack_message(
                            token=SLACK_TOKEN,
                            channel=SLACK_CHANNEL,
                            subject=subject,
                            body=body
                        )
                        if slack_ts:
                            self.log(f"Sent Slack message with timestamp: {slack_ts}")
                            success = True
                        else:
                            self.log("Failed to send Slack message")

                    # Send Telegram message if enabled
                    if TELEGRAM_ENABLED:
                        telegram_success = send_telegram_message(
                            bot_token=TELEGRAM_BOT_TOKEN,
                            chat_id=TELEGRAM_CHAT_ID,
                            subject=subject,
                            body=body
                        )
                        if telegram_success:
                            self.log("Sent Telegram message")
                            success = True
                        else:
                            self.log("Failed to send Telegram message")

                    # Send Discord message if enabled
                    if DISCORD_ENABLED:
                        discord_success = send_discord_message(
                            webhook_url=DISCORD_WEBHOOK_URL,
                            subject=subject,
                            body=body
                        )
                        if discord_success:
                            self.log("Sent Discord message")
                            success = True
                        else:
                            self.log("Failed to send Discord message")

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
                            self.log("Sent custom webhook")
                            success = True
                        else:
                            self.log("Failed to send custom webhook")

                    # Mark the email as read if any notification was sent successfully
                    if success:
                        if mark_as_read(imap, email_id):
                            self.log(f"Marked email {email_id.decode()} as read")
                        else:
                            self.log(f"Failed to mark email {email_id.decode()} as read")
                    else:
                        self.log(f"No successful notifications sent for email {email_id.decode()}")

            except Exception as e:
                self.log(f"An error occurred: {e}")
            finally:
                # Ensure the IMAP connection is properly closed
                if imap:
                    try:
                        imap.logout()
                    except Exception as e:
                        self.log(f"Error while logging out from IMAP: {e}")
                # Wait before checking for new emails again based on check interval
                time.sleep(CHECK_INTERVAL)


if __name__ == '__main__':
    # Initialize the main Tkinter window
    root = tk.Tk()
    app = EmailMonitorApp(root)
    root.mainloop()
