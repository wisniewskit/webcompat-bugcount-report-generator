#!/usr/bin/python3

import json
import os
import requests
import time

from datetime import datetime
from dateutil.relativedelta import relativedelta
from requests_html import HTMLSession
from tablib import Dataset

DATA_PATH = os.path.join(os.getcwd(), 'data/top-sites.csv')
EXPORT_PATH = os.path.join(os.getcwd(), 'data/export/{}.csv'.format(
    datetime.now().strftime('%Y%m%d-%H%M%S')))
GITHUB_API_TOKEN = os.environ.get('GITHUB_API_TOKEN')
REQUEST_HEADERS = {
    'Authorization': 'token {}'.format(GITHUB_API_TOKEN),
    'User-Agent': 'mozilla/webcompat-bugcount-report-generator'}


def get_websites(dataset):
    websites = dataset.get_col(0)
    return websites


s = requests.Session()
s.headers.update(REQUEST_HEADERS)


def api_request(*args, **kwargs):
    try:
        # try to delay getting rate limited
        time.sleep(3)
        response = s.get(*args, **kwargs)
        response.raise_for_status()
        print(response)
        return response
    except requests.exceptions.HTTPError as e:
        json_response = json.loads(response.text)
        print(e)
        print(json_response['message'])
        print('Sleeping...')
        time.sleep(60)
        return api_request(*args, **kwargs)


def get_col_c(website):
    '''
    Column C represents "Fresh Bugzilla" bugs.
    '''
    # we want to add the dot back for Bugzilla search
    website = website.replace(' ', '.')
    last_year = datetime.now() - relativedelta(years=1)
    template = 'https://bugzilla.mozilla.org/buglist.cgi?f1=OP&bug_file_loc_type=allwordssubstr&o3=greaterthan&list_id=14636479&v3={date}&resolution=---&bug_file_loc={site}&query_format=advanced&f3=creation_ts&bug_status=UNCONFIRMED&bug_status=NEW&bug_status=ASSIGNED&bug_status=REOPENED&product=Core&product=Fenix&product=Firefox%20for%20Android&product=Firefox%20for%20Echo%20Show&product=Firefox%20for%20FireTV&product=Firefox%20for%20iOS&product=GeckoView&product=Web%20Compatibility'  # noqa
    query = template.format(site=website, date=last_year.strftime("%Y-%m-%d"))
    session = HTMLSession()
    r = session.get(query)
    try:
        count_el = r.html.find('span.bz_result_count', first=True)
        count = int(count_el.text.rstrip('bugs found.'))
    except:  # noqa
        count = 0
    return '=HYPERLINK("{}"; {})'.format(query, count)


def get_col_d(website):
    '''
    Column D represents open webcompat bugs that have the `engine-gecko` label.
    That should be:
    browser-firefox, browser-firefox-mobile,
    browser-firefox-tablet, browser-fenix,
    browser-focus-geckoview, browser-firefox-reality
    '''
    template = 'https://github.com/search?p=8&q={}+in%3Atitle+repo%3Awebcompat%2Fweb-bugs%2F+state%3Aopen+label:engine-gecko&type=Issues'  # noqa
    query = template.format(website)
    search_template = 'https://api.github.com/search/issues?q={}+in%3Atitle+repo%3Awebcompat%2Fweb-bugs%2F+state%3Aopen+label:engine-gecko&type=Issues'  # noqa
    search = search_template.format(website)
    response = api_request(search).json()
    count = response['total_count']
    return '=HYPERLINK("{}"; {})'.format(query, count)


def get_col_e(website):
    '''
    Column E represents severity-critical webcompat bugs
    '''
    template = 'https://github.com/webcompat/web-bugs/issues?q={}+in%3Atitle+repo%3Awebcompat%2Fweb-bugs%2F+is%3Aopen+label%3Aseverity-critical+label:engine-gecko'  # noqa
    query = template.format(website)
    search_template = 'https://api.github.com/search/issues?q={}+in%3Atitle+repo%3Awebcompat%2Fweb-bugs%2F+is%3Aopen+label%3Aseverity-critical+label:engine-gecko'  # noqa
    search = search_template.format(website)
    response = api_request(search).json()
    count = response['total_count']
    return '=HYPERLINK("{}"; {})'.format(query, count)


if __name__ == '__main__':
    dataset_in = Dataset(headers=['Website'])
    dataset_in.load(open(DATA_PATH, 'rb').read().decode('utf-8'), format='csv')

    dataset_out = Dataset(headers=[
        'Website',
        'fresh 🐞s',
        'webcompat.com 🐞s',
        'severity-critical 🐞s',
        'needsdiagnosis 🐞s',
        'sitewait 🐞s',
    ])

    websites = get_websites(dataset_in)
    for website in websites:
        # replace the period with a space, because GitHub search is weird.
        website = website.replace('.', ' ')
        row = [
            website,
            get_col_c(website),
            get_col_d(website),
            get_col_e(website),
            get_col_f(website),
            get_col_g(website),
        ]

        print(row)
        dataset_out.append(row)

    with open(EXPORT_PATH, 'wb') as f:
        f.write(dataset_out.csv.encode('utf-8'))
