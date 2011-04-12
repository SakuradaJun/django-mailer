django-mailer by James Tauber <http://jtauber.com/>
http://code.google.com/p/django-mailer/

A reusable Django app for queuing the sending of email



# Forked to support multiple accounts and email throttling.

First draft on April 12, 2011 - may not work. 

Forked to allow `django-mailer` to use multiple email accounts and to impose a daily sending limit per email account.

Specifically made for Google Apps users who have a 500 email a day per user sending limit and are also limited to a `from_address` that is the actual authenticated account.

If you'd like to use different "from" emails, it's currently not an option with google apps.




## Options

### DAILY_SENDING_LIMIT  
Specify an optional `DAILY_SENDING_LIMIT` in `settings.py` to limit the amount of emails per 24 hours.

Throttling is done via emails sent in the last 24 hours, not discrete days.



### MULTIPLE ACCOUNTS  
send_mail takes an extra keyword argument, `account`, which is an integer mapped to a specific account in `settings.py`.

Account 0 is mapped to the default email settings `EMAIL_HOST`, `EMAIL_PORT`, etc. 

Account 1 is mapped to `EMAIL1_HOST`, `EMAIL1_PORT`, etc. 

All settings below are required and mailer will complain if it fails to find a setting.

    # settings.py
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_HOST_USER = 'foo@example.com'
    EMAIL_HOST_PASSWORD = 'password'
    EMAIL_USE_TLS = True

    EMAIL1_HOST = 'smtp.gmail.com'
    EMAIL1_PORT = 587
    EMAIL1_HOST_USER = 'bar@example.com'
    EMAIL1_HOST_PASSWORD = 'password'
    EMAIL1_USE_TLS = True

## Usage

    from mailer import send_mail

    send_mail("Subject", "Body", "from@example.com", ["to@example.com"]) # uses default email settings
    send_mail("Subject", "Body", "from@example.com", ["to@example.com"], account=1) # uses EMAIL1_* settings
    send_mail("Subject", "Body", "from@example.com", ["to@example.com"], account=2) # uses EMAIL1_* settings

    bash $ python manage.py send_mail
    # iterates through Messages by account and sends up to DAILY_SENDING_LIMIT per account if specified.