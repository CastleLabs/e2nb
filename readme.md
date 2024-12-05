# Email Monitor and Notification System
## Complete Documentation

## Table of Contents
1. [Introduction](#introduction)
2. [Installation](#installation)
3. [User Guide](#user-guide)
4. [Configuration](#configuration)
5. [Technical Reference](#technical-reference)
6. [Troubleshooting](#troubleshooting)

## Introduction

The Email Monitor and Notification System is a Python-based application that monitors email inboxes for unread messages and forwards notifications through various channels including SMS, Voice Call, WhatsApp, Slack, Telegram, Discord, and Custom Webhooks. It features a graphical user interface (GUI) for easy configuration and monitoring.

### Key Features
- Real-time email monitoring
- Multiple notification channels
- Configurable email filtering
- User-friendly GUI
- Flexible configuration options
- Detailed logging system

## Installation

### Prerequisites
```bash
# Required Python packages
pip install twilio
pip install slack_sdk
pip install requests
pip install tkinter
```

### Configuration File
The application uses a `config.ini` file for storing settings. If not present, it will be created automatically with default values.

## User Guide

### Starting the Application
1. Run the Python script:
```bash
python email_monitor.py
```

### Main Interface
The application interface is organized into several tabs:
- **Email Settings**: Configure email server connection
- **Settings**: General application settings
- **Notification Methods**: Enable/disable notification channels
- **Notification-specific tabs**: Configure individual notification services
- **Logs**: View application activity

### Basic Setup
1. Configure Email Settings:
   - Enter IMAP server details
   - Provide email credentials
   - Set email filters (optional)

2. Enable Notification Methods:
   - Check desired notification methods
   - Configure each selected method

3. Start Monitoring:
   - Click "Start Monitoring"
   - View activity in the Logs tab

### Stopping the Application
- Click "Stop Monitoring" to halt email checking
- Close the application window

## Configuration

### Email Settings
- `imap_server`: IMAP server address (e.g., "imap.gmail.com")
- `imap_port`: Server port (typically 993 for SSL)
- `username`: Email address
- `password`: Email password
- `filter_emails`: Comma-separated list of email addresses or domains to monitor

### General Settings
- `max_sms_length`: Maximum length for SMS messages
- `check_interval`: Time between email checks (seconds)

### Notification Settings
Each notification method has specific configuration requirements:

#### Twilio (SMS/Voice/WhatsApp)
- Account SID
- Auth Token
- From Number
- To Number(s)

#### Slack
- Bot Token
- Channel Name

#### Telegram
- Bot Token
- Chat ID

#### Discord
- Webhook URL

#### Custom Webhook
- Webhook URL

## Technical Reference

### Core Functions

#### Configuration Management

##### `load_config(config_file=CONFIG_FILE_PATH)`
Loads configuration from the specified INI file.

**Parameters:**
- `config_file`: Path to configuration file (default: 'config.ini')

**Returns:**
- `configparser.ConfigParser`: Configuration object

**Example:**
```python
config = load_config('custom_config.ini')
```

##### `save_config(config, config_file=CONFIG_FILE_PATH)`
Saves configuration to the specified INI file.

**Parameters:**
- `config`: Configuration object
- `config_file`: Target file path

##### `create_default_config(config_file=CONFIG_FILE_PATH)`
Creates a default configuration file.

**Parameters:**
- `config_file`: Target file path

#### Email Operations

##### `connect_to_imap(server, port, username, password)`
Establishes connection to IMAP server.

**Parameters:**
- `server`: IMAP server address
- `port`: Server port
- `username`: Email username
- `password`: Email password

**Returns:**
- `imaplib.IMAP4_SSL`: Connected IMAP object or None on failure

##### `fetch_unread_emails(imap)`
Retrieves unread emails from the inbox.

**Parameters:**
- `imap`: Connected IMAP object

**Returns:**
- List of tuples: (email_id, email_message)

##### `extract_email_body(msg)`
Extracts plain text body from email message.

**Parameters:**
- `msg`: Email message object

**Returns:**
- `str`: Email body text

##### `mark_as_read(imap, email_id)`
Marks an email as read.

**Parameters:**
- `imap`: IMAP connection
- `email_id`: Email identifier

**Returns:**
- `bool`: Success status

#### Notification Functions

##### `send_sms_via_twilio(account_sid, auth_token, from_number, to_number, body)`
Sends SMS using Twilio.

**Parameters:**
- `account_sid`: Twilio account SID
- `auth_token`: Twilio auth token
- `from_number`: Sender's number
- `to_number`: Recipient's number
- `body`: Message content

**Returns:**
- `str`: Message SID or None on failure

##### `make_voice_call(account_sid, auth_token, from_number, to_number, message)`
Initiates voice call via Twilio.

**Parameters:**
- `account_sid`: Twilio account SID
- `auth_token`: Twilio auth token
- `from_number`: Caller number
- `to_number`: Recipient's number
- `message`: Message to read

**Returns:**
- `str`: Call SID or None on failure

##### `send_whatsapp_message(account_sid, auth_token, from_number, to_number, body)`
Sends WhatsApp message via Twilio.

**Parameters:**
- `account_sid`: Twilio account SID
- `auth_token`: Twilio auth token
- `from_number`: Sender's WhatsApp number
- `to_number`: Recipient's WhatsApp number
- `body`: Message content

**Returns:**
- `str`: Message SID or None on failure

##### `send_slack_message(token, channel, subject, body)`
Sends message to Slack channel.

**Parameters:**
- `token`: Slack bot token
- `channel`: Target channel
- `subject`: Message subject
- `body`: Message content

**Returns:**
- `str`: Message timestamp or None on failure

##### `send_telegram_message(bot_token, chat_id, subject, body)`
Sends message via Telegram.

**Parameters:**
- `bot_token`: Telegram bot token
- `chat_id`: Target chat ID
- `subject`: Message subject
- `body`: Message content

**Returns:**
- `bool`: Success status

##### `send_discord_message(webhook_url, subject, body)`
Sends message to Discord channel.

**Parameters:**
- `webhook_url`: Discord webhook URL
- `subject`: Message subject
- `body`: Message content

**Returns:**
- `bool`: Success status

##### `send_custom_webhook(webhook_url, payload)`
Sends data to custom webhook.

**Parameters:**
- `webhook_url`: Target webhook URL
- `payload`: Data to send

**Returns:**
- `bool`: Success status

### GUI Class: EmailMonitorApp

#### Main Methods

##### `__init__(self, root)`
Initializes the application GUI.

**Parameters:**
- `root`: Tkinter root window

##### `create_widgets(self)`
Creates all GUI elements.

##### `save_settings(self)`
Saves current configuration to file.

##### `start_monitoring(self)`
Initiates email monitoring process.

##### `stop_monitoring(self)`
Stops email monitoring process.

##### `log(self, message)`
Adds message to log display.

**Parameters:**
- `message`: Log message text

##### `monitor_emails(self)`
Main email monitoring loop.

## Troubleshooting

### Common Issues

#### Connection Errors
1. Verify IMAP server settings
2. Check network connectivity
3. Confirm firewall settings

#### Authentication Failures
1. Verify credentials
2. Check for two-factor authentication
3. Confirm app-specific password requirements

#### Notification Issues
1. Verify API credentials
2. Check rate limits
3. Confirm network connectivity

### Logging
- Check the Logs tab for detailed error messages
- Review application output for additional details

### Support
For additional support:
1. Check configuration
2. Review error messages
3. Verify network connectivity
4. Contact system administrator

## Best Practices

### Security
1. Use environment variables for sensitive data
2. Regularly update credentials
3. Implement proper access controls

### Performance
1. Adjust check interval based on needs
2. Monitor resource usage
3. Implement proper error handling

### Maintenance
1. Regular configuration backups
2. Log rotation
3. Regular updates

## Conclusion

This documentation provides comprehensive coverage of the Email Monitor and Notification System. For additional assistance or to report issues, please contact the system administrator or refer to the troubleshooting section.
