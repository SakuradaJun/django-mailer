import time
import smtplib
import logging
import datetime

from lockfile import FileLock, AlreadyLocked, LockTimeout
from socket import error as socket_error

from django.conf import settings
from django.core.mail import send_mail as core_send_mail
try:
    # Django 1.2
    from django.core.mail import get_connection
except ImportError:
    # ImportError: cannot import name get_connection
    from django.core.mail import SMTPConnection
    get_connection = lambda backend=None, fail_silently=False, **kwds: SMTPConnection(fail_silently=fail_silently)

from mailer.models import Message, DontSendEntry, MessageLog


# when queue is empty, how long to wait (in seconds) before checking again
EMPTY_QUEUE_SLEEP = getattr(settings, "MAILER_EMPTY_QUEUE_SLEEP", 30)

# lock timeout value. how long to wait for the lock to become available.
# default behavior is to never wait for the lock to be available.
LOCK_WAIT_TIMEOUT = getattr(settings, "MAILER_LOCK_WAIT_TIMEOUT", -1)

# The actual backend to use for sending, defaulting to the Django default.
EMAIL_BACKEND = getattr(settings, "MAILER_EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")

# Get daily sending limit
DAILY_SENDING_LIMIT = getattr(settings, 'MAILER_DAILY_SENDING_LIMIT', 0)


def prioritize(account=0):
    """
    Yield the messages in the queue in the order they should be sent
    based on a specific account.
    """
    while True:
        while Message.objects.high_priority(account).count() or Message.objects.medium_priority(account).count():
            while Message.objects.high_priority(account).count():
                for message in Message.objects.high_priority(account).order_by("when_added"):
                    yield message
            while Message.objects.high_priority(account).count() == 0 and Message.objects.medium_priority(account).count():
                yield Message.objects.medium_priority(account).order_by("when_added")[0]
        while Message.objects.high_priority(account).count() == 0 and Message.objects.medium_priority(account).count() == 0 and Message.objects.low_priority(account).count():
            yield Message.objects.low_priority(account).order_by("when_added")[0]
        if Message.objects.non_deferred(account).count() == 0:
            break


def send_all():
    """
    Send all eligible messages in the queue.
    """
    
    lock = FileLock("send_mail")
    
    logging.debug("acquiring lock...")
    try:
        lock.acquire(LOCK_WAIT_TIMEOUT)
    except AlreadyLocked:
        logging.debug("lock already in place. quitting.")
        return
    except LockTimeout:
        logging.debug("waiting for the lock timed out. quitting.")
        return
    logging.debug("acquired.")
    
    start_time = time.time()
    
    kw_settings_map = dict(host='HOST', port='PORT', username='HOST_USER', password='HOST_PASSWORD', use_tls='USE_TLS',)
    
    try:
        for account in Message.objects.filter(priority__lt=4).values_list('account', flat=True).annotate():
            connection_kwargs = {}
            incomplete = False # easier than refactoring to function
            for kw, setting in kw_settings_map.iteritems():
                try:
                    connection_kwargs[kw] = getattr(settings, 'EMAIL{account}_{setting}'.format(
                        account=account or '', setting=setting))
                except AttributeError, e:
                    logging.warn(e)
                    incomplete = True
                    break
                    
            if incomplete:
                logging.warn('Skipping account {account} due to failure to pull settings'.format(account=account))
                continue
            
            logging.debug("Sending mail for account {account}".format(account=account))
            
            dont_send = 0
            deferred = 0
            sent = 0
            
            sent_today_count = MessageLog.objects.filter(account=account, result="1",
                when_attempted__gt=datetime.datetime.now() - datetime.timedelta(days=1),).count()
                
            logging.debug("Account {account} has successfully sent {count} emails in the past 24 hours".format(
                account=account, count=sent_today_count))
            
            connection = None
            for message in prioritize(account):
                try:
                    if DAILY_SENDING_LIMIT and (sent_today_count + sent) >= DAILY_SENDING_LIMIT:
                        logging.warn("daily sending limit of {limit} reached - aborting".format(
                            limit=DAILY_SENDING_LIMIT))
                        break
                    if connection is None:
                        # use custom login parameters based on email account 
                        connection = get_connection(backend=EMAIL_BACKEND, **connection_kwargs)
                        
                    logging.debug("sending message '%s' to %s from account %s (%s/%s limit)" % (message.subject.encode("utf-8"), u", ".join(message.to_addresses).encode("utf-8"), account, (sent_today_count + sent), DAILY_SENDING_LIMIT ))
                    email = message.email
                    email.connection = connection
                    email.send()
                    MessageLog.objects.log(message, 1, account=account) # @@@ avoid using literal result code
                    message.delete()
                    sent += 1
                except (socket_error, smtplib.SMTPSenderRefused, smtplib.SMTPRecipientsRefused, smtplib.SMTPAuthenticationError), err:
                    message.defer()
                    logging.warn("message deferred due to failure: %s" % err)
                    MessageLog.objects.log(message, 3, log_message=str(err), account=account) # @@@ avoid using literal result code
                    deferred += 1
                    # Get new connection, it case the connection itself has an error.
                    connection = None
                    
            logging.debug("")
            logging.debug("Account %s: %s sent; %s deferred;" % (account, sent, deferred))
    finally:
        logging.debug("releasing lock...")
        lock.release()
        logging.debug("released.")
    
    logging.debug("done in %.2f seconds" % (time.time() - start_time))

def send_loop():
    """
    Loop indefinitely, checking queue at intervals of EMPTY_QUEUE_SLEEP and
    sending messages if any are on queue.
    """
    
    while True:
        while not Message.objects.all():
            logging.debug("sleeping for %s seconds before checking queue again" % EMPTY_QUEUE_SLEEP)
            time.sleep(EMPTY_QUEUE_SLEEP)
        send_all()
