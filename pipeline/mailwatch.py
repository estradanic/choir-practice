#!/usr/bin/env python3
"""Start a score job by email: send a .mscz attachment to the agents' inbox.
Saves it to scores/ (picked up by watch.sh); the email body is saved to scores/notes/<name>.txt
and passed to the agent as the user's answers. Only senders in MAIL_ALLOWED (comma separated) whose
mail passes SPF or DKIM are accepted. Usage: mailwatch.py   (one pass; watch.sh calls it regularly)"""
import email, email.policy, imaplib, os, re, smtplib, ssl, sys, time
from email.message import EmailMessage
from email.utils import parseaddr

sys.path.insert(0, os.path.dirname(__file__))
from ask import env, body

ROOT = os.path.join(os.path.dirname(__file__), '..')
MAX = 30 * 1024 * 1024


def main():
    e = env()
    allowed = {a.strip().lower() for a in e.get('MAIL_ALLOWED', '').split(',') if a.strip()}
    if not allowed: return
    ctx = ssl.create_default_context()
    local = e.get('MAIL_IMAP_HOST', '127.0.0.1') == '127.0.0.1'
    if local: ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    h, pt = e.get('MAIL_IMAP_HOST', '127.0.0.1'), int(e.get('MAIL_IMAP_PORT', 1143))
    if pt == 993: im = imaplib.IMAP4_SSL(h, pt, ssl_context=ctx)
    else: im = imaplib.IMAP4(h, pt); im.starttls(ctx)
    im.login(e['MAIL_USER'], e['MAIL_BRIDGE_PASSWORD']); im.select('INBOX')
    for i in im.search(None, 'UNSEEN')[1][0].split():
        m = email.message_from_bytes(im.fetch(i, '(BODY.PEEK[])')[1][0][1], policy=email.policy.default)
        atts = [a for a in m.iter_attachments() if (a.get_filename() or '').lower().endswith('.mscz')]
        if not atts: continue
        im.store(i, '+FLAGS', '\\Seen')
        sender = parseaddr(str(m['From']))[1].lower()
        auth = str(m.get('Authentication-Results', '')).lower()
        if sender not in allowed or not ('spf=pass' in auth or 'dkim=pass' in auth):
            print('rejected mail from', sender, file=sys.stderr); continue
        data = atts[0].get_content()
        if not data.startswith(b'PK') or len(data) > MAX:
            reply(e, m, 'Rejected: that does not look like a valid .mscz (or it is too large).'); continue
        name = re.sub(r"[^\w .,'()&-]", '_', os.path.basename(atts[0].get_filename())[:-5]).strip(' .') or 'score'
        scores = os.path.join(ROOT, 'scores')
        if any(os.path.exists(os.path.join(scores, d, name + '.mscz')) for d in ('', 'in-progress')):
            name += time.strftime(' %m%d-%H%M')
        os.makedirs(os.path.join(scores, 'notes'), exist_ok=True)
        note = body(m)
        if note: open(os.path.join(scores, 'notes', name + '.txt'), 'w').write(note)
        tmp = os.path.join(scores, '.' + name + '.part')
        open(tmp, 'wb').write(data)
        os.rename(tmp, os.path.join(scores, name + '.mscz'))
        reply(e, m, f'Got "{name}". Starting the import' + (' with your note.' if note else '.'))
    im.logout()


def reply(e, m, text):
    r = EmailMessage(); r['From'], r['To'] = e['MAIL_USER'], parseaddr(str(m['From']))[1]
    r['Subject'] = 'Re: ' + str(m['Subject']); r['In-Reply-To'] = m['Message-ID']; r.set_content(text)
    ctx = ssl.create_default_context()
    h, pt = e.get('MAIL_SMTP_HOST', '127.0.0.1'), int(e.get('MAIL_SMTP_PORT', 1025))
    if h == '127.0.0.1': ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    if pt == 465: c = smtplib.SMTP_SSL(h, pt, context=ctx)
    else: c = smtplib.SMTP(h, pt); c.starttls(context=ctx)
    with c: c.login(e['MAIL_USER'], e['MAIL_BRIDGE_PASSWORD']); c.send_message(r)


if __name__ == '__main__':
    import time
    main()
