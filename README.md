# Simple Enroll Bot

Simple Enroll Bot is a Python script that automates the enrollment process for Stanford University courses. It constantly updates the user's planned courses and attempts to enroll them in the background so they can slip in if there is an opening.

## Installation

To use this script, you need to have Python 3 installed on your system. You also need to install the required packages using the following command:

```bash
pip install -r requirements.txt
```

## Usage

Before running the script, you need to create a `credentials.json` file in the same directory as the script. The file should contain your username (suid) and password for logging into Simple Enroll. For example:

```json
{
    "username": "suid",
    "password": "password"
}
```

Don't worry, these are only kept locally.

You also need to plan your courses on Simple Enroll and make sure they are in the "Planned Courses" section.

To run the script, use the following command:

```bash
python src/bot.py
```

The script will open a headless Chrome browser and log into Simple Enroll using your credentials. It will then try to enroll you in your planned courses every 5 minutes. It will also display a live table of your courses and their status on the terminal.

If you need to use two-factor authentication (2FA) for logging in, the script will wait for you to approve it on your device. It will also save your Duo Security cookies so that you don't need to do 2FA again.

To stop the script, press Ctrl+C on the terminal. The script will quit gracefully and close the browser.

## Disclaimer

This script is for educational purposes only and is not affiliated with or endorsed by Stanford University. Use it at your own risk and responsibility. The author is not liable for any consequences that may arise from using this script.
