import zip
import str
import csv
import requests.exceptions
import pyparsing as parse
import urllib.parse
import dateutil.parser
from ckanext.spatial.harvesters.base import guess_standard


def add_status():
    records = open('wafurls.txt')
    results = open('wafurlsstatus.txt', 'w+')
    headers = 'count,count_with_date,server,status_code,error,standard,id,unapproved,url'
    results.write(headers + '\n')
    writer = csv.DictWriter(
        results, headers.split(',')
    )

    for row in records:
        row_dict = dict(list(zip('id unapproved url'.split(), row.split())))
        try:
            response = requests.get(row_dict['url'], timeout=60)
            content = response.content
            server = str(response.headers.get('server'))
            if server == 'Microsoft-IIS/7.5':
                scraper = 'iis'
            elif 'apache' in server.lower() or 'nginx' in server.lower() or not response.headers.get('server'):
                scraper = 'apache'
            else:
                scraper = 'other'

            row_dict['status_code'] = str(response.status_code)
            row_dict['server'] = server

            if content and response.status_code == 200:
                extracted_waf = extract_waf(content, row_dict['url'], scraper)
                row_dict['count'] = str(len(extracted_waf))
                row_dict['count_with_date'] = str(len([i for i in extracted_waf if i[1]]))
                if extracted_waf:
                    try:
                        content_doc = requests.get(extracted_waf[0][0], timeout=60).content
                        standard = guess_standard(content_doc)
                        row_dict['standard'] = standard
                    except Exception as e:
                        print(('Error guessing format. Error is ', e))
            else:
                row_dict['count'] = "0"
                row_dict['count_with_date'] = "0"
        except Exception as e:
            row_dict['error'] = str(e)
            row_dict['count'] = "0"
            row_dict['count_with_date'] = "0"

        writer.writerow(row_dict)
        results.flush()


apache = parse.SkipTo(parse.CaselessLiteral("<a href="), include=True).suppress() \
    + parse.quotedString.setParseAction(parse.removeQuotes).setResultsName('url') \
    + parse.SkipTo("</a>", include=True).suppress() \
    + parse.Optional(parse.Literal('</td><td align="right">')).suppress() \
    + parse.Optional(parse.Combine(
        parse.Word(parse.alphanums + '-') + parse.Word(parse.alphanums + ':'),
        adjacent=False, joinString=' ').setResultsName('date'))

iis = parse.SkipTo("<br>").suppress() \
    + parse.OneOrMore("<br>").suppress() \
    + parse.Optional(parse.Combine(
        parse.Word(parse.alphanums + '/') + parse.Word(parse.alphanums + ':') + parse.Word(parse.alphas),
        adjacent=False, joinString=' ').setResultsName('date')) \
    + parse.Word(parse.nums).suppress() \
    + parse.Literal('<A HREF=').suppress() \
    + parse.quotedString.setParseAction(parse.removeQuotes).setResultsName('url')

other = parse.SkipTo(parse.CaselessLiteral("<a href="), include=True).suppress() \
    + parse.quotedString.setParseAction(parse.removeQuotes).setResultsName('url')


scrapers = {'apache': parse.OneOrMore(parse.Group(apache)),
            'other': parse.OneOrMore(parse.Group(other)),
            'iis': parse.OneOrMore(parse.Group(iis))}


def extract_waf(content, base_url, scraper, results=None, depth=0):
    if results is None:
        results = []

    base_url = base_url.rstrip('/').split('/')
    if 'index' in base_url[-1]:
        base_url.pop()
    base_url = '/'.join(base_url)
    base_url += '/'

    parsed = scrapers[scraper].parseString(content)

    for record in parsed:
        url = record.url
        if not url:
            continue
        if url.startswith('_'):
            continue
        if '?' in url:
            continue
        if '#' in url:
            continue
        if 'mailto:' in url:
            continue
        if '..' not in url and url[0] != '/' and url[-1] == '/':
            new_depth = depth + 1
            if depth > 10:
                print('max depth reached')
                continue
            new_url = urllib.parse.urljoin(base_url, url)
            if not new_url.startswith(base_url):
                continue
            print(('new_url', new_url))
            try:
                response = requests.get(new_url)
                content = response.content
            except Exception as e:
                print(str(e))
                continue
            extract_waf(content, new_url, scraper, results, new_depth)
            continue
        if not url.endswith('.xml'):
            continue
        date = record.date
        if date:
            try:
                date = str(dateutil.parser.parse(date))
            except Exception:
                date = None
        results.append((urllib.parse.urljoin(base_url, record.url), date))

    return results


if __name__ == '__main__':
    add_status()
