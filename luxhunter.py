# -*- coding: utf-8 -*-
__author__ = 'apqlzm'

import requests
import codecs
from lxml import etree
import smtplib
import string
import argparse
import getpass
from datetime import datetime, timedelta


def notify(email_text, dst_email):
    """
    Function sends emails.
    :param email_text:
    :return:
    """
    smtpobj = smtplib.SMTP_SSL('poczta.o2.pl', 465)

    smtpobj.ehlo()
    smtpobj.login('abusemenot@tlen.pl', 'ABUSEMENOTLUXMED123')

    from_ = 'powiadomienie@o-wizycie.pl',
    to_ = dst_email
    subject_ = 'Szukana wizyta jest dostepna w placowce Luxmed'
    text_ = email_text
    body_ = string.join(("From: %s" % from_, "To: %s" % to_, "Subject: %s" % subject_, "", text_), "\r\n")
    smtpobj.sendmail('abusemenot@tlen.pl', [to_], body_)
    smtpobj.quit()


def wtf(text, file_path='log.html'):
    """
    Write To File
    :param text: text which will be written to file
    :return:
    """
    out = codecs.open(file_path, mode='w', encoding='utf-8')
    out.write(unicode(text))
    out.close()


def log_in(login, password):
    """
    Login to Luxmed's patient portal
    :param login: Luxmed account login. Usually e-mail address.
    :param password: You know...
    :return: Session object.
    """
    log_in_params = {'Login': login, 'Password': password}
    s = requests.Session()
    s.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:37.0) Gecko/20100101 Firefox/37.0'})
    s.headers.update({'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'})
    s.headers.update({'Referer': 'https://portalpacjenta.luxmed.pl/PatientPortal/Account/LogOn'})
    s.cookies.update({'LXCookieMonit': '1'})
    r = s.post('https://portalpacjenta.luxmed.pl/PatientPortal/Account/LogIn', data=log_in_params)

    if 'Zarezerwuj' in r.text:
        print 'Login succeed'
        return s
    else:
        print 'Login failed'
        return None


def log_out(session):
    """
    Log out from Luxmed's patient portal
    :param session: Session object
    :return
    """
    r = session.get('https://portalpacjenta.luxmed.pl/PatientPortal/Account/LogOut')
    if 'bezpiecznie wylogowany' in r.text:
        print 'Logout succeed'
    else:
        print 'Logout failed'


def find(session, service_id, date_from, date_to, doctor_id, city_id, clinic_id, time_option, payer_id):
    """
    Find appointment.
    :param session: session object is created during log in and passed to the function
    :param service_id: type of service example: orthopaedist, general practitioner
    :param date_from: date range start
    :param date_to: date range end
    :param doctor_id: not all of them are worth your health ;)
    :param city_id:
    :param clinic_id: 
    :param time_option: Morning, Afternoon, Evening or Any
    :param payer_id: 
    :return:
    """

    main_page_url = 'https://portalpacjenta.luxmed.pl/PatientPortal/'
    search_POST_url = 'https://portalpacjenta.luxmed.pl/PatientPortal/Reservations/Reservation/PartialSearch'
    search_page_url = 'https://portalpacjenta.luxmed.pl/PatientPortal/Reservations/Coordination/Activity?actionId=90'

    main_page = session.get(main_page_url)
    search_page = session.get(search_page_url)

    parser = etree.HTMLParser()

    main_page_tree = etree.fromstring(main_page.text, parser)
    search_page_tree = etree.fromstring(search_page.text, parser)

    verification_token = main_page_tree.xpath('//*[@id="PageMainContainer"]/input/@value')

    coordinationActivityId = search_page_tree.xpath('//*[@id="CoordinationActivityId"]/@value')
    isFFS = search_page_tree.xpath('//*[@id="IsFFS"]/@value')
    isDisabled = search_page_tree.xpath('//*[@id="IsDisabled"]/@value')
    payersCount = search_page_tree.xpath('//*[@id="PayersCount"]/@value')    
    
    search_params = {
        '__RequestVerificationToken': verification_token[0],
        'CoordinationActivityId': coordinationActivityId[0],
        'IsFFS': isFFS[0],
        'IsDisabled': isDisabled[0],
        'PayersCount': payersCount[0],
        'DateOption': 'SelectedDate',
        'FilterType': 'Coordination',
        'MaxPeriodLength': '0',
        'PayersCount': '0',
        'FromDate': date_from,
        'ToDate': date_to,
        'CustomRangeSelected': 'true',
        'CityId': city_id,
        'ServiceId': service_id,
        'TimeOption': '0',
        'PayerId': payer_id,
        'LanguageId': '10'
        }

    result = session.post(search_POST_url, data=search_params)

    wtf(unicode(result.text))

    if is_appointment_available(result.text):
        print 'Hurray! Visit has been found :)'
        return True, result.text.encode('utf-8')
    else:
        print 'Pity :( Visit has not been found.'
        return False, ""


def is_appointment_available(html_page):
    """
    Let's see if you found your appointment.
    :param html_page: web page source
    :return: True if you are lucky
    """
    if 'Brak dostępnych termin'.decode('utf-8') in unicode(html_page):
        return False
    if 'Nowe terminy wizyt pojawiaj'.decode('utf-8') in unicode(html_page):
        return False
    else:
        return True

def main():
    """
    Main function where everything happens.
    1. Login to the website
    2. Check if queried appointment is available
    3. Do something with it
    4. Logout
    :return:
    """

    today_date = datetime.today().strftime('%Y-%m-%d')
    month_later_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

    parser = argparse.ArgumentParser(description='Luxmed appointment availability checker.')
    parser.add_argument('--lxlogin', help='Luxmed account login', required=True)
    parser.add_argument('--lxpass', help='Luxmed account password', required=True)
    parser.add_argument('--email', help='Email address', required=True)
    parser.add_argument('--payerid', help='Payer ID', required=True)
    parser.add_argument('--datefrom', help='Date format dd-mm-yyyy. Default is current date.', default=today_date, required=False)
    parser.add_argument('--dateto', help='Date format dd-mm-yyyy. Default is month from today.', default=month_later_date, required=False)
    parser.add_argument('--serviceid', help='Type of specialist. ID should be taken from csv in repository.', required=False)
    parser.add_argument('--doctorid', help='Doctor id. ID should be take from csv in repository.', default=0, required=False)
    parser.add_argument('--cityid', help='City id. ID should be taken from csv in repository.', required=True)
    parser.add_argument('--clinicid', help='Clinic id. ID should be taken from csv in repository.', default='')
    parser.add_argument('--timeoption', help='Time option from range: Morning, Afternoon, Evening or Any', default='Any')
    args = parser.parse_args()

    session = log_in(args.lxlogin, args.lxpass)
    isav, result = find(session, service_id=args.serviceid, date_from=args.datefrom, date_to=args.dateto, doctor_id=args.doctorid, city_id=args.cityid, clinic_id=args.clinicid, time_option=args.timeoption, payer_id=args.payerid)
    
    if isav:
        notify('Wizyta znaleziona: %s' % result, args.email)
    log_out(session)

if __name__ == '__main__':
    main()