# E2NB (Email to Notification Blaster)

A powerful Python application that monitors email inboxes and forwards notifications through multiple channels including SMS, Voice, WhatsApp, Slack, Telegram, Discord, and custom webhooks.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.6%2B-blue)
![Alt Text](emailsettings.png "Hover Title")

## 📚 Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Notification Channels](#notification-channels)
- [API Reference](#api-reference)
- [GUI Reference](#gui-reference)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## ✨ Features

- 📧 Real-time email inbox monitoring
- 🔔 Multiple notification channels
- 🎯 Configurable email filtering
- 🖥️ User-friendly GUI
- ⚙️ Flexible configuration options
- 📝 Detailed logging system
- 🔒 Secure credential handling

## 🚀 Installation

### Prerequisites

- Python 3.6 or higher
- Required packages:

```bash
pip install -r requirements.txt
```

Or install packages individually:

```bash
pip install twilio
pip install slack_sdk
pip install requests
pip install tkinter
```

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/e2nb.git
cd e2nb
```

2. Create configuration file:
```bash
python e2nb.py
```
The application will automatically create a `config.ini` file on first run.

## 🏃‍♂️ Quick Start

1. Run the application:
```bash
python e2nb.py
```

2. Configure email settings in the GUI:
   - IMAP server details
   - Email credentials
   - Optional email filters

3. Enable desired notification channels:
   - Select notification methods
   - Configure channel settings

4. Start monitoring and check the logs

## ⚙️ Configuration

### Email Settings

| Setting | Description | Example |
|---------|-------------|---------|
| `imap_server` | IMAP server address | imap.gmail.com |
| `imap_port` | Server port (SSL) | 993 |
| `username` | Email address | user@example.com |
| `password` | Email password | ******** |
| `filter_emails` | Email filters | @domain.com, user@example.com |

### General Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `max_sms_length` | Maximum SMS length | 1600 |
| `check_interval` | Email check interval (seconds) | 60 |

## 📱 Notification Channels

### Twilio (SMS/Voice/WhatsApp)

Required settings:
```ini
[Twilio]
enabled = True
account_sid = your_account_sid
auth_token = your_auth_token
from_number = +1234567890
destination_number = +1234567890
```

### Slack

Required settings:
```ini
[Slack]
enabled = True
token = xoxb-your-bot-token
channel = #channel-name
```

### Telegram

Required settings:
```ini
[Telegram]
enabled = True
bot_token = your-bot-token
chat_id = your-chat-id
```

### Discord

Required settings:
```ini
[Discord]
enabled = True
webhook_url = your-webhook-url
```

### Custom Webhook

Required settings:
```ini
[CustomWebhook]
enabled = True
webhook_url = your-webhook-url
```

## 📚 API Reference

### Configuration Management

#### `load_config(config_file='config.ini')`

Load application configuration from INI file.

```python
def load_config(config_file='config.ini'):
    """
    Load configuration from INI file.

    Args:
        config_file (str): Path to configuration file
        
    Returns:
        configparser.ConfigParser: Configuration object
        
    Example:
        config = load_config('custom_config.ini')
    """
```

#### `save_config(config, config_file='config.ini')`

Save configuration changes to INI file.

```python
def save_config(config, config_file='config.ini'):
    """
    Save configuration to INI file.
    
    Args:
        config (configparser.ConfigParser): Configuration to save
        config_file (str): Target file path
    """
```

### Email Operations

#### `connect_to_imap(server, port, username, password)`

Establish secure IMAP connection.

```python
def connect_to_imap(server, port, username, password):
    """
    Connect to IMAP server securely.
    
    Args:
        server (str): IMAP server address
        port (int): Server port number
        username (str): Email username
        password (str): Email password
        
    Returns:
        imaplib.IMAP4_SSL: Connected IMAP object or None on failure
    
    Example:
        imap = connect_to_imap('imap.gmail.com', 993, 'user@gmail.com', 'password')
    """
```

#### `fetch_unread_emails(imap)`

Fetch unread messages from inbox.

```python
def fetch_unread_emails(imap):
    """
    Get unread emails from inbox.
    
    Args:
        imap (imaplib.IMAP4_SSL): Connected IMAP object
        
    Returns:
        list: Tuples of (email_id, email_message)
    """
```

### Notification Services

#### SMS Notifications

```python
def send_sms_via_twilio(account_sid, auth_token, from_number, to_number, body):
    """
    Send SMS via Twilio.
    
    Args:
        account_sid (str): Twilio account SID
        auth_token (str): Twilio auth token
        from_number (str): Sender's phone number
        to_number (str): Recipient's phone number
        body (str): Message content
        
    Returns:
        str: Message SID or None on failure
        
    Example:
        sid = send_sms_via_twilio(
            'AC123...', 
            'auth_token',
            '+1234567890',
            '+9876543210',
            'Hello from E2NB!'
        )
    """
```

#### Voice Calls

```python
def make_voice_call(account_sid, auth_token, from_number, to_number, message):
    """
    Make voice call via Twilio.
    
    Args:
        account_sid (str): Twilio account SID
        auth_token (str): Twilio auth token
        from_number (str): Caller's number
        to_number (str): Recipient's number
        message (str): Message to read
        
    Returns:
        str: Call SID or None on failure
    """
```

#### Chat Platforms

##### Slack

```python
def send_slack_message(token, channel, subject, body):
    """
    Send message to Slack channel.
    
    Args:
        token (str): Slack bot token
        channel (str): Target channel name
        subject (str): Message subject
        body (str): Message content
        
    Returns:
        str: Message timestamp or None on failure
        
    Example:
        ts = send_slack_message(
            'xoxb-token',
            '#notifications',
            'New Email',
            'Email content here'
        )
    """
```

##### Telegram

```python
def send_telegram_message(bot_token, chat_id, subject, body):
    """
    Send message via Telegram.
    
    Args:
        bot_token (str): Telegram bot token
        chat_id (str): Target chat ID
        subject (str): Message subject
        body (str): Message content
        
    Returns:
        bool: Success status
    """
```

## 🖥️ GUI Reference

### Main Window

The application window contains several tabs:

1. **Email Settings Tab**
   - IMAP server configuration
   - Credentials
   - Email filters

2. **Settings Tab**
   - General application settings
   - Check intervals
   - Message limits

3. **Notification Methods Tab**
   - Enable/disable channels
   - Service-specific settings

4. **Logs Tab**
   - Real-time activity monitoring
   - Error reporting

### GUI Methods

```python
class EmailMonitorApp:
    def __init__(self, root):
        """
        Initialize application GUI.
        
        Args:
            root (tk.Tk): Tkinter root window
        """
        
    def start_monitoring(self):
        """Start email monitoring process."""
        
    def stop_monitoring(self):
        """Stop email monitoring process."""
        
    def log(self, message):
        """
        Add message to log display.
        
        Args:
            message (str): Log message text
        """
```

## 🔧 Troubleshooting

### Common Issues

#### Connection Errors
- Verify IMAP server settings
- Check network connectivity
- Confirm firewall settings

#### Authentication Issues
- Verify credentials
- Check 2FA settings
- Confirm app-specific passwords

#### Notification Problems
- Verify API credentials
- Check service status
- Monitor rate limits

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

## 📞 Support

For support:
1. Check [Troubleshooting](#troubleshooting) section
2. Review error messages in logs
3. Open GitHub issue
4. Contact maintainers

---

Built with ❤️ by [Your Name]
