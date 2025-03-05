import os
from datetime import datetime
import sqlite3
from flask import Flask, request, Response
from twilio.rest import Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

app = Flask(__name__)

class TennisCourtBookingBot:
    def __init__(self):
        self.twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        self.setup_database()
        self.current_state = {}

    def setup_database(self):
        """Initialize SQLite database for bookings"""
        db_path = os.path.join('database', 'tennis_bookings.db')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY,
                    user_id TEXT,
                    username TEXT,
                    court_date TEXT,
                    court_time TEXT,
                    UNIQUE(user_id, court_date)
                )
                """
            )
            conn.commit()

    def send_whatsapp_message(self, to_number, message):
        """Send a WhatsApp message"""
        self.twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=message,
            to=to_number
        )

    def process_message(self, user_id, user_number, message):
        """Process incoming WhatsApp message"""
        if message.lower() == "hi":
            response = "Welcome to Tennis Court Booking! Choose an option:\n1. Book Court\n2. View Bookings"
            self.send_whatsapp_message(user_number, response)
        elif message == "1":
            self.send_whatsapp_message(user_number, "Enter your name:")
        else:
            self.send_whatsapp_message(user_number, "Invalid option. Try again.")

bot = TennisCourtBookingBot()

@app.route("/whatsapp", methods=['POST'])
def whatsapp_webhook():
    from_number = request.form.get("From")
    message_body = request.form.get("Body")
    bot.process_message(from_number, from_number, message_body)
    return Response(status=200)

# Run on Railway with Gunicorn
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use Railway's dynamic port
    app.run(host='0.0.0.0', port=port)
