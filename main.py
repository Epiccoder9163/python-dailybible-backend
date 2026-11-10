# Script for automatically sending email newsletter based on email template and data

import os
import csv
from datetime import date
import smtplib
import ssl
import requests
import re
import io
import smtplib
from email.message import EmailMessage
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv

# Configure debugging
debugging_enabled = False

# Configure sending methods
email = True
groupme = True

VERSE_START = re.compile(r"^\s*[1-3]?\s*[A-Za-z]+\s+\d+:\d+\b")

def get_reference(reference):
    out = ""
    verse_lines = []
    found = False
    with open("bible.txt", "r", encoding="utf-8") as f:
        for line in f:
            if not found:
                # Match the requested reference only at the start of a line,
                # followed by whitespace or the end of the line.
                if line.lstrip().startswith(reference) and (
                    len(line.lstrip()) == len(reference)
                    or line.lstrip()[len(reference)].isspace()
                ):
                    verse_lines.append(line.strip())
                    found = True
            else:
                # Stop when the next verse reference begins.
                if VERSE_START.match(line):
                    break

                # Skip blank lines; include wrapped continuation text.
                if line.strip():
                    verse_lines.append(line.strip())

        if not found:
            return None

    # Remove the reference from the first line and join wrapped lines.
    verse_lines[0] = verse_lines[0][len(reference):].strip()
    out = (" ".join(verse_lines))
    return out

# --- Email specific functions ---
def render_email(today, name, reference, verse, header):
    # Set up basic jinja2 environment
    env = Environment(loader = FileSystemLoader('templates'))
    # Load the template
    template = env.get_template('email.jinja')

    # Render the template, given the variables
    output = template.render(
        name = name,
        reference = reference,
        verse = verse,
        header = header
    )

    return output

def send_email(email, domain, secret, subject, recipient, content):
    # Email variables
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = email
    msg['To'] = recipient
    # Add HTML content to email
    msg.set_content(content, subtype='html')

    # Authenticate with secret and send email
    with smtplib.SMTP_SSL(domain, 465) as smtp:
        smtp.login(msg['From'], secret)
        smtp.send_message(msg)

# --- GroupMe specific functions ---
def render_groupme(verse, reference):
    # Set up basic jinja2 environment
    env = Environment(loader = FileSystemLoader('templates'))
    # Load the template
    template = env.get_template('groupme.jinja')

    # Render the template, given the variables
    output = template.render(
        reference = reference,
        verse = verse
    )

    return output

def send_groupme(bot_id, access_token, content):
    # Use an HTTP(S) POST request to publish a message
    url = "https://api.groupme.com/v3/bots/post"
    payload = {
        "bot_id": bot_id,
        "text": content
    }
    headers = {
        "X-Access-Token": access_token
    }
    response = requests.post(url, json=payload, headers=headers)
    print(response.status_code)
    print(response.text)  
    response.raise_for_status()


def main():
    # Grab today's date, in year-month-day format
    today = date.today()
    print(today)

    # Parse people in mailing list
    with open("people.csv", "r") as f:
        people = list(csv.reader(f))
    
    # Open data.csv and search for today's date in any of the columns
    with open("data.csv", "r") as f:
        data = list(csv.reader(f))
        print(data)
        for item in data:
            if str(today) in item:
                data_now = item
                break
    print(data_now)
    # data_now[0] - date
    # data_now[1] - title
    # data_now[2] - references

    # Split multiple comma-delimeted references into a list
    references = re.split(",",data_now[2])
    new_references = []
    # Add a space to the compressed list to help with searching
    for item in references:
        new_references.append(item[:3] + " " + item[3:])
    print(new_references)
    references = new_references

    # Get relevant verses
    verses = ""
    for i in references:
        verse = get_reference(i)
        verses += verse + " "

    print(verses)

    # Combine references list into a single string
    reference = ""
    for j in references:
        if j == references[-1]:
            reference += j
        else:
            reference += j + ", "
    
    # If email sending is enabled send emails
    if email == True:
        for i in people:
            # Render the new html file 
            out = render_email(today, i[0], reference, verses, data_now[1])

            # If debugging is enabled, do not send email
            # Instead, write output to html file for in-browser viewing
            if debugging_enabled == True:
                # Using io.open() function
                html = "./out/" + i[0] + ".html"

                # Open the file in write mode using io.open()
                with io.open(html, 'w', encoding='utf-8') as file:
                    # Write content to the file
                    file.write(out)
            else:
                # Load environment file to grab secrets
                load_dotenv()
                smtp_email = os.getenv('email')
                smtp_password = os.getenv('password')
                smtp_server = os.getenv('smtp_server')

                # Send final email with correct parameters
                send_email(smtp_email, smtp_server, smtp_password, data_now[1], i[1], out)
    
    # If groupme support is enabled send groupme message
    if groupme == True:
        # Render GroupMe message
        out = render_groupme(verses, reference)
        
        # If debugging is enabled, do not send GroupMe message
        # Instead, write output to txt file (groupme_message.txt)
        if debugging_enabled == True:
                # Using io.open() function
                txt = "./out/groupme_message.txt"

                # Open the file in write mode using io.open()
                with io.open(txt, 'w', encoding='utf-8') as file:
                    # Write content to the file
                    file.write(out)
        else:
            # Load environment file to grab secrets
            load_dotenv()
            bot_id = os.getenv('bot_id')
            access_token = os.getenv('access_token')

            # Send final GroupMe message
            send_groupme(bot_id, access_token, out)

# Run main function        
main()
