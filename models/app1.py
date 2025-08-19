from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()


account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_number = os.getenv("TWILIO_PHONE_NUMBER")

client = Client(account_sid, auth_token)


message = client.messages.create(
    body="Hello Bhargavi, testing inbound!",
    from_='+18147871499',
    to='+9988987678'  
)

print(f"Message sent! SID: {message.sid}")