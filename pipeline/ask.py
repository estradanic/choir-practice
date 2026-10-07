#!/usr/bin/env python3
"""Email a question via Proton Bridge and block until you reply. Prints the reply.
Usage: ask.py <piece> "<question>"   (env from .env: MAIL_USER, MAIL_BRIDGE_PASSWORD, MAIL_TO)"""
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
        if l.startswith('>') or re.match(r'^On .* wrote:$', l.strip()): break
        out.append(l)
    return '\n'.join(out).strip()

def main(piece, question, notify_only=False):
    e = env()
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    tag = f'[choir:{piece}]'
    msg = EmailMessage()
    msg['From'], msg['To'] = e['MAIL_USER'], e.get('MAIL_TO', e['MAIL_USER'])
    msg['Subject'] = f'{tag} {question.splitlines()[0][:60]}'
    mid = make_msgid(domain='choir.local'); msg['Message-ID'] = mid
    msg.set_content(question + ('' if notify_only else '\n\n(Reply to this email with your answer.)'))
    with smtplib.SMTP('127.0.0.1', 1025) as s:
        s.starttls(context=ctx); s.login(e['MAIL_USER'], e['MAIL_BRIDGE_PASSWORD']); s.send_message(msg)
    if notify_only: return ''
    deadline = time.time() + 7 * 86400
    seen = set()
    while time.time() < deadline:
        try:
            im = imaplib.IMAP4('127.0.0.1', 1143); im.starttls(ctx); im.login(e['MAIL_USER'], e['MAIL_BRIDGE_PASSWORD'])
            im.select('INBOX')
            _, ids = im.search(None, 'SUBJECT', f'"{tag}"')
            for i in ids[0].split():
                if i in seen: continue
                seen.add(i)
                _, d = im.fetch(i, '(RFC822)')
                m = email.message_from_bytes(d[0][1], policy=email.policy.default)
                if mid in (m.get('In-Reply-To') or '') + (m.get('References') or '') or (
                        m['Subject'].lower().startswith('re:') and tag in m['Subject'] and m['Message-ID'] != mid):
                    r = body(m)
                    if r: im.logout(); return r
            im.logout()
        except Exception as ex:
            print('imap retry:', ex, file=sys.stderr)
        time.sleep(20)
    sys.exit('timed out waiting for reply')

if __name__ == '__main__':
    import email.policy
    notify = '--notify' in sys.argv
    a = [x for x in sys.argv[1:] if x != '--notify']
    print(main(a[0], a[1], notify))
