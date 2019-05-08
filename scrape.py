#!/usr/bin/python3

import json
import os
import re
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
    Column C represents Bugzilla bugs created after the DX Epoch (2018-01-01).
    '''
    # we want to add the dot back for Bugzilla search
    website = website.replace(' ', '.')
    template = 'https://bugzilla.mozilla.org/buglist.cgi?f1=OP&bug_file_loc_type=allwordssubstr&o3=greaterthan&list_id=14636479&v3=2018&resolution=---&bug_file_loc={site}&query_format=advanced&f3=creation_ts&bug_status=UNCONFIRMED&bug_status=NEW&bug_status=ASSIGNED&bug_status=REOPENED&product=Core&product=Fenix&product=Firefox%20for%20Android&product=Firefox%20for%20Echo%20Show&product=Firefox%20for%20FireTV&product=Firefox%20for%20iOS&product=GeckoView&product=Web%20Compatibility&keywords_type=nowords&keywords=meta%2C%20&status_whiteboard_type=notregexp&status_whiteboard=sci%5C-exclude'  # noqa
    query = template.format(site=website)
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


def get_col_h(website):
    '''
    Column H represents duplicates (webcompat.com see-also links on Bugzilla
    which are also marked as duplicates on webcompat.com)

    To do so, an advanced Bugzilla search is first done to get all bugs for
    a given site with any see-alsos on webcompat.com:
    - See Also contains any of the strings: webcompat.com,github.com/webcompat
    - Status contains any of the strings: UNCONFIRMED,NEW,ASSIGNED,REOPENED
    - URL contains the string (exact case): (website)

    Then GitHub queries are run to confirm how many of the discovered issues
    are in the duplicate milestone.
    '''
    see_also_template = 'https://bugzilla.mozilla.org/rest/bug?include_fields=id,see_also&f1=see_also&f2=bug_status&f3=bug_file_loc&o1=anywordssubstr&o2=anywordssubstr&o3=casesubstring&v1=webcompat.com%2Cgithub.com%2Fwebcompat&v2=UNCONFIRMED%2CNEW%2CASSIGNED%2CREOPENED&v3={site}&limit=0'  # noqa
    see_also_query = see_also_template.format(site=website)
    session = HTMLSession()
    response = session.get(see_also_query)
    json_response = json.loads(response.text)

    github_issues_to_check = []
    for bug in json_response['bugs']:
        bz_id = bug["id"]
        for see_also_link in bug["see_also"]:
            if see_also_link.find("webcompat.com") >= 0 or\
               see_also_link.find("github.com/webcompat") >= 0:
                github_id = re.search("/(\d+)", see_also_link).group(1)
                github_issues_to_check.append([github_id, bz_id])

    # GitHub search queries (q parameter) cannot be too long, so do >1 requests
    searches = []
    base_search_query = "is%3Aissue+milestone%3Aduplicate+repo%3Awebcompat%2Fweb-bugs%2F"
    search_query = base_search_query
    search_map_gh_to_bz = {}
    id_index = 0
    while id_index < len(github_issues_to_check):
        github_id, bz_id = github_issues_to_check[id_index]
        id_index += 1
        if len(search_query) + 1 + len(github_id) > 256:
            searches.append([search_query, search_map_gh_to_bz])
            search_query = base_search_query
            search_map_gh_to_bz = {}
        search_query += "+" + github_id
        search_map_gh_to_bz[int(github_id)] = bz_id
    searches.append([search_query, search_map_gh_to_bz])

    count = 0
    duped_bz_ids = set()
    for [query, gh_to_bz_map] in searches:
        milestone_template = 'https://api.github.com/search/issues?per_page=100&q={query}'  # noqa
        milestone_search = milestone_template.format(query=query)
        response = api_request(milestone_search).json()
        if response['incomplete_results']:
            raise "Should not have over 100 results for just {n} search items".format(len(ids))
        for item in response["items"]:
            bz_id = gh_to_bz_map.get(item["number"])
            if bz_id is not None and item["milestone"]["title"] == "duplicate":
                duped_bz_ids.add(bz_id)
                count += 1

    if count:
        param = "%2C".join(str(id) for id in duped_bz_ids)
        bz_link = "https://bugzilla.mozilla.org/buglist.cgi?o1=anyexact&v1={ids}&f1=bug_id".format(ids=param)
        return '=HYPERLINK("{}"; {})'.format(bz_link, count)
    else:
        return "0"


if __name__ == '__main__':
    dataset_in = Dataset(headers=['Website'])
    dataset_in.load(open(DATA_PATH, 'rb').read().decode('utf-8'), format='csv')

    dataset_out = Dataset(headers=[
        'Website',
        'fresh 🐞s',
        'webcompat.com 🐞s',
        'severity-critical 🐞s',
        'duplicate 🐞s',
    ])

    websites = get_websites(dataset_in)
    for idx, website in enumerate(websites):
        # replace the period with a space, because GitHub search is weird.
        space_website = website.replace('.', ' ')
        row = [
            website,
            get_col_c(space_website),
            get_col_d(space_website),
            get_col_e(space_website),
            get_col_h(website),
        ]

        print(idx, website)
        dataset_out.append(row)

    with open(EXPORT_PATH, 'wb') as f:
        f.write(dataset_out.csv.encode('utf-8'))
