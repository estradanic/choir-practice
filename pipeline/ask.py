#!/usr/bin/env python3
"""Email a question via Proton Bridge and block until you reply. Prints the reply.
Usage: ask.py <piece> "<question>"   (env from .env: MAIL_USER, MAIL_BRIDGE_PASSWORD, MAIL_TO; optional MAIL_SMTP_HOST/PORT, MAIL_IMAP_HOST/PORT, defaults = Proton Bridge; port 465/993 use SSL)"""
import email, email.policy, imaplib, os, re, smtplib, ssl, sys, time
from email.message import EmailMessage
from email.utils import make_msgid

def env():
    d = {}
    p = os.path.join(os.path.dirname(__file__), '..', '.env')
    for l in open(p):
        if '=' in l and not l.startswith('#'):
            k, v = l.rstrip('\n').split('=', 1); d[k] = v.strip().strip('"\'')
    return d

def body(m):
    p = m.get_body(('plain',)) if hasattr(m, 'get_body') else None
    t = p.get_content() if p else ''
    out = []
    for l in t.splitlines():
        if l.startswith('>') or l.startswith('-----') or re.match(r'^On .* wrote:$', l.strip()): break
        out.append(l)
    return '\n'.join(out).strip()

def main(piece, question, notify_only=False):
    e = env()
    ctx = ssl.create_default_context()
    if e.get('MAIL_SMTP_HOST', '127.0.0.1') == '127.0.0.1': ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

    def send(m):
        h, pt = e.get('MAIL_SMTP_HOST', '127.0.0.1'), int(e.get('MAIL_SMTP_PORT', 1025))
        if pt == 465: c = smtplib.SMTP_SSL(h, pt, context=ctx)
        else: c = smtplib.SMTP(h, pt); c.starttls(context=ctx)
        with c: c.login(e['MAIL_USER'], e['MAIL_BRIDGE_PASSWORD']); c.send_message(m)

    def imap_login():
        h, pt = e.get('MAIL_IMAP_HOST', '127.0.0.1'), int(e.get('MAIL_IMAP_PORT', 1143))
        if pt == 993: im = imaplib.IMAP4_SSL(h, pt, ssl_context=ctx)
        else: im = imaplib.IMAP4(h, pt); im.starttls(ctx)
        im.login(e['MAIL_USER'], e['MAIL_BRIDGE_PASSWORD']); return im
    tag = f'[choir:{piece}]'
    msg = EmailMessage()
    msg['From'], msg['To'] = e['MAIL_USER'], e.get('MAIL_TO', e['MAIL_USER'])
    msg['Subject'] = f'{tag} {question.splitlines()[0][:60]}'
    mid = make_msgid(domain='choir.local'); msg['Message-ID'] = mid
    msg.set_content(question + ('' if notify_only else '\n\n(Reply to this email with your answer.)'))
    send(msg)
    if notify_only: return ''
    deadline = time.time() + 7 * 86400
    seen = set()
    remind = time.time() + 4 * 3600
    while time.time() < deadline:
        try:
            im = imap_login()
            im.select('INBOX')
            _, ids = im.search(None, 'SUBJECT', '"choir:"')
            for i in ids[0].split():
                if i in seen: continue
                seen.add(i)
                _, d = im.fetch(i, '(RFC822)')
                m = email.message_from_bytes(d[0][1], policy=email.policy.default)
                if tag not in str(m['Subject']): continue
                if mid in (m.get('In-Reply-To') or '') + (m.get('References') or '') or (
                        m['Subject'].lower().startswith('re:') and tag in m['Subject'] and m['Message-ID'] != mid):
                    r = body(m)
                    if r: im.logout(); return r
            im.logout()
        except Exception as ex:
            print('imap retry:', ex, file=sys.stderr)
        if time.time() > remind:
            remind = time.time() + 4 * 3600
            try:
                r = EmailMessage(); r['From'], r['To'] = msg['From'], msg['To']
                r['Subject'] = f'Reminder {tag} still waiting for your reply'
                r.set_content('Still waiting on your reply to:\n\n' + question)
                send(r)
            except Exception as ex:
                print('reminder failed:', ex, file=sys.stderr)
        time.sleep(20)
    sys.exit('timed out waiting for reply')

if __name__ == '__main__':
    import email.policy
    notify = '--notify' in sys.argv
    a = [x for x in sys.argv[1:] if x != '--notify']
    print(main(a[0], a[1], notify))
