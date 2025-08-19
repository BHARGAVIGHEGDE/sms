--> **Two-Way SMS Chat with Twilio**

I built this project to explore two-way SMS communication using Twilio US numbers. The goal was to create a simple system where you can send messages and instantly receive replies — just like a real chat.

 -->**What it does**

Send SMS messages from a Twilio-powered US number

Receive replies in real time using webhooks

Store all conversations (sent + received) in a database

Easily view message history for tracking or debugging

--> **Tech Stack**

Twilio API – to send/receive SMS

Webhooks – to catch incoming messages

[ backend tech –  Python Flask]

Database – MySQL

 --> **How it works**

I send an SMS from my Twilio number.

The recipient replies back to the same number.

Twilio calls my webhook with the reply.

My backend processes & saves the conversation.

I can see the full chat history whenever I want.


This project was a great way to get hands-on with Twilio APIs and understand how two-way texting systems are built. It can be extended into customer support chatbots, appointment reminders, or any service that needs reliable SMS communication.
