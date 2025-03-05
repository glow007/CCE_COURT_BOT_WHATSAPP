import os
from datetime import datetime, timedelta
import sqlite3

from twilio.rest import Client
from flask import Flask, request, Response
import threading

# Twilio WhatsApp credentials
TWILIO_ACCOUNT_SID = 'your_account_sid'
TWILIO_AUTH_TOKEN = 'your_auth_token'
TWILIO_WHATSAPP_NUMBER = 'whatsapp:+14155238886'  # Twilio's WhatsApp sandbox number

class TennisCourtBookingBot:
    def __init__(self, account_sid, auth_token):
        self.twilio_client = Client(account_sid, auth_token)
        self.setup_database()
        self.current_state = {}  # Track conversation state for each user

    def setup_database(self):
        """Initialize SQLite database for bookings"""
        with sqlite3.connect("tennis_bookings.db") as conn:
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

    def send_whatsapp_message(self, to_number, message, reply_markup=None):
        """Send a WhatsApp message"""
        body = message
        if reply_markup:
            body += "\n\n" + "\n".join(reply_markup)
        
        self.twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=body,
            to=to_number
        )

    def get_main_menu_options(self):
        """Create main menu options"""
        return [
            "1. Book Court",
            "2. My Schedule", 
            "3. Reschedule",
            "4. Cancel Booking"
        ]

    def handle_start(self, user_id, user_number):
        """Handle bot start/welcome message"""
        self.current_state[user_id] = 'MAIN_MENU'
        welcome_message = (
            "Welcome to Tennis Court Booking Bot! 🎾\n"
            "Please choose an option:\n"
        )
        self.send_whatsapp_message(
            user_number, 
            welcome_message + "\n".join(self.get_main_menu_options())
        )

    def handle_main_menu_selection(self, user_id, user_number, selection):
        """Handle main menu selection"""
        if selection == '1':
            self.current_state[user_id] = 'BOOK_NAME'
            self.send_whatsapp_message(user_number, "What's your name?")
        
        elif selection == '2':
            bookings = self.get_user_bookings(user_id)
            if bookings:
                message = "Your current bookings:\n" + "\n".join([
                    f"Date: {booking[0]}, Time: {booking[1]}" 
                    for booking in bookings
                ])
            else:
                message = "You have no current bookings."
            self.send_whatsapp_message(user_number, message)
            self.handle_start(user_id, user_number)  # Return to main menu
        
        elif selection == '3':
            self.current_state[user_id] = 'RESCHEDULE_SELECT_BOOKING'
            bookings = self.get_user_bookings(user_id)
            if bookings:
                message = "Select a booking to reschedule:\n" + "\n".join([
                    f"{i+1}. Date: {booking[0]}, Time: {booking[1]}" 
                    for i, booking in enumerate(bookings)
                ])
                self.send_whatsapp_message(user_number, message)
            else:
                message = "You have no bookings to reschedule."
                self.send_whatsapp_message(user_number, message)
                self.handle_start(user_id, user_number)
        
        elif selection == '4':
            self.current_state[user_id] = 'CANCEL_BOOKING'
            bookings = self.get_user_bookings(user_id)
            if bookings:
                message = "Select a booking to cancel:\n" + "\n".join([
                    f"{i+1}. Date: {booking[0]}, Time: {booking[1]}" 
                    for i, booking in enumerate(bookings)
                ])
                self.send_whatsapp_message(user_number, message)
            else:
                message = "You have no bookings to cancel."
                self.send_whatsapp_message(user_number, message)
                self.handle_start(user_id, user_number)

    def book_name(self, user_id, user_number, name):
        """Handle booking name input"""
        self.current_state[user_id] = 'BOOK_DATE'
        # Store name temporarily
        self.current_state[f'{user_id}_name'] = name
        self.send_whatsapp_message(
            user_number, 
            "What date would you like to book? (YYYY-MM-DD)"
        )

    def book_date(self, user_id, user_number, date):
        """Handle booking date input"""
        try:
            # Validate date format
            datetime.strptime(date, '%Y-%m-%d')
            self.current_state[user_id] = 'BOOK_TIME'
            # Store date temporarily
            self.current_state[f'{user_id}_date'] = date
            self.send_whatsapp_message(
                user_number, 
                "What time would you like to book? (HH:MM)"
            )
        except ValueError:
            self.send_whatsapp_message(
                user_number, 
                "Invalid date format. Please use YYYY-MM-DD"
            )

    def book_time(self, user_id, user_number, time):
        """Handle booking time input"""
        try:
            # Validate time format
            datetime.strptime(time, '%H:%M')
            
            # Retrieve stored data
            name = self.current_state.get(f'{user_id}_name', '')
            date = self.current_state.get(f'{user_id}_date', '')
            
            # Confirm booking
            self.current_state[user_id] = 'BOOK_CONFIRM'
            confirm_message = (
                f"Confirm booking?\n"
                f"Name: {name}\n"
                f"Date: {date}\n"
                f"Time: {time}\n\n"
                "Reply 'yes' to confirm or 'no' to cancel."
            )
            self.send_whatsapp_message(user_number, confirm_message)
        except ValueError:
            self.send_whatsapp_message(
                user_number, 
                "Invalid time format. Please use HH:MM"
            )

    def book_confirm(self, user_id, user_number, response):
        """Handle booking confirmation"""
        if response.lower() == 'yes':
            name = self.current_state.get(f'{user_id}_name', '')
            date = self.current_state.get(f'{user_id}_date', '')
            time = self.current_state.get(f'{user_id}_time', '')
            
            # Save booking to database
            with sqlite3.connect("tennis_bookings.db") as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "INSERT INTO bookings (user_id, username, court_date, court_time) VALUES (?, ?, ?, ?)",
                        (user_id, name, date, time)
                    )
                    conn.commit()
                    self.send_whatsapp_message(
                        user_number, 
                        "Booking confirmed successfully!"
                    )
                except sqlite3.IntegrityError:
                    self.send_whatsapp_message(
                        user_number, 
                        "You already have a booking on this date."
                    )
        else:
            self.send_whatsapp_message(
                user_number, 
                "Booking cancelled."
            )
        
        # Clear temporary state and return to main menu
        self.handle_start(user_id, user_number)

    def get_user_bookings(self, user_id):
        """Retrieve user's bookings"""
        with sqlite3.connect("tennis_bookings.db") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT court_date, court_time FROM bookings WHERE user_id = ?", 
                (user_id,)
            )
            return cursor.fetchall()

    def process_message(self, user_id, user_number, message):
        """Process incoming WhatsApp message"""
        current_state = self.current_state.get(user_id, 'INITIAL')

        if current_state == 'INITIAL' or current_state == 'MAIN_MENU':
            # Check if message is a main menu selection
            if message in ['1', '2', '3', '4']:
                self.handle_main_menu_selection(user_id, user_number, message)
            else:
                self.handle_start(user_id, user_number)
        
        elif current_state == 'BOOK_NAME':
            self.book_name(user_id, user_number, message)
        
        elif current_state == 'BOOK_DATE':
            self.book_date(user_id, user_number, message)
        
        elif current_state == 'BOOK_TIME':
            # Store time and move to confirmation
            self.current_state[f'{user_id}_time'] = message
            self.book_time(user_id, user_number, message)
        
        elif current_state == 'BOOK_CONFIRM':
            self.book_confirm(user_id, user_number, message)
        
        # Add similar logic for reschedule and cancel booking states

def create_flask_app(bot):
    """Create Flask app to handle WhatsApp webhooks"""
    app = Flask(__name__)

    @app.route("/whatsapp", methods=['POST'])
    def whatsapp_webhook():
        # Extract message details from Twilio request
        from_number = request.form.get('From')
        message_body = request.form.get('Body')

        # Process the message
        bot.process_message(from_number, from_number, message_body)

        return Response(status=200)

    return app

def run_flask_server(app):
    """Run Flask server"""
    app.run(host='0.0.0.0', port=5000)

def main():
    # Initialize bot with Twilio credentials
    bot = TennisCourtBookingBot(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    
    # Create Flask app
    flask_app = create_flask_app(bot)
    
    # Run Flask server in a separate thread
    server_thread = threading.Thread(target=run_flask_server, args=(flask_app,))
    server_thread.start()

if __name__ == "__main__":
    main()
