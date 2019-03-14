import os
import requests
import time

from datetime import datetime
from requests_html import HTMLSession
from tablib import Dataset


DATA_PATH = os.path.join(os.getcwd(), 'data/top-sites-report-card.xslx')
EXPORT_PATH = os.path.join(os.getcwd(), 'data/export/{}.csv'.format(datetime.now().strftime('%Y%m%d-%H%M%S')))
GITHUB_API_TOKEN = os.environ.get('GITHUB_API_TOKEN')


def get_websites(dataset):
    websites = dataset.get_col(1)
    return websites

def api_request(*args, **kwargs):
    try:
        response = requests.get(*args, **kwargs)
        response.raise_for_status()
        print(response)
        return response
    except requests.exceptions.HTTPError:
        print('Sleeping...')
        time.sleep(60)
        return api_request(*args, **kwargs)

def get_col_c(website):
    template = 'https://bugzilla.mozilla.org/buglist.cgi?bug_file_loc_type=allwordssubstr&list_id=14485116&resolution=---&bug_file_loc={}&query_format=advanced&bug_status=UNCONFIRMED&bug_status=NEW&bug_status=ASSIGNED&bug_status=REOPENED&product=Core&product=Firefox&product=Firefox%20for%20Android&product=Web%20Compatibility'
    query = template.format(website)
    session = HTMLSession()
    r = session.get(query)
    try:
        count_el = r.html.find('span.bz_result_count', first=True)
        count = int(count_el.text.rstrip('bugs found.'))
    except:
        count = 0
    return '=HYPERLINK("{}"; {})'.format(query, count)

def get_col_d(website):
    template = 'https://github.com/search?p=8&q={}+in%3Atitle+repo%3Awebcompat%2Fweb-bugs%2F+state%3Aopen&type=Issues'
    query = template.format(website)
    search_template = 'https://api.github.com/search/issues?q={}+in%3Atitle+repo%3Awebcompat%2Fweb-bugs%2F+state%3Aopen&type=Issues'
    search = search_template.format(website)
    response = api_request(search, headers = {'Authorization': 'token {}'.format(GITHUB_API_TOKEN)}).json()
    count = response['total_count']
    return '=HYPERLINK("{}"; {})'.format(query, count)

def get_col_e(website):
    template = 'https://github.com/webcompat/web-bugs/issues?q={}+in%3Atitle+repo%3Awebcompat%2Fweb-bugs%2F+is%3Aopen+label%3Aseverity-critical+'
    query = template.format(website)
    search_template = 'https://api.github.com/search/issues?q={}+in%3Atitle+repo%3Awebcompat%2Fweb-bugs%2F+is%3Aopen+label%3Aseverity-critical+'
    search = search_template.format(website)
    response = api_request(search, headers = {'Authorization': 'token {}'.format(GITHUB_API_TOKEN)}).json()
    count = response['total_count']
    return '=HYPERLINK("{}"; {})'.format(query, count)

def get_col_f(website):
    template = 'https://github.com/search?p=8&q={}+in%3Atitle+repo%3Awebcompat%2Fweb-bugs%2F+is%3Aopen+milestone%3Aneedsdiagnosis'
    query = template.format(website)
    search_template = 'https://api.github.com/search/issues?q={}+in%3Atitle+repo%3Awebcompat%2Fweb-bugs%2F+is%3Aopen+milestone%3Aneedsdiagnosis'
    search = search_template.format(website)
    response = api_request(search, headers = {'Authorization': 'token {}'.format(GITHUB_API_TOKEN)}).json()
    count = response['total_count']
    return '=HYPERLINK("{}"; {})'.format(query, count)

def get_col_g(website):
    template = 'https://github.com/webcompat/web-bugs/issues?q={}+in%3Atitle+repo%3Awebcompat%2Fweb-bugs%2F+is%3Aopen+milestone%3Asitewait'
    query = template.format(website)
    search_template = 'https://api.github.com/search/issues?q={}+in%3Atitle+repo%3Awebcompat%2Fweb-bugs%2F+is%3Aopen+milestone%3Asitewait'
    search = search_template.format(website)
    response = api_request(search, headers = {'Authorization': 'token {}'.format(GITHUB_API_TOKEN)}).json()
    count = response['total_count']
    return '=HYPERLINK("{}"; {})'.format(query, count)


if __name__ == '__main__':
    dataset_in = Dataset()
    dataset_in.load(open(DATA_PATH, 'rb').read())

    dataset_out = Dataset(headers=[
        'Website',
        'Bugzilla',
        'Github - open',
        'Github - severity-critical',
        'Github - needsdiagnosis',
        'Github - sitewait'
    ])

    websites = get_websites(dataset_in)
    for website in websites:
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

    with open(EXPORT_PATH, 'w') as f:
        f.write(dataset_out.csv)
