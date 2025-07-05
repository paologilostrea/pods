# scrape_to_podcast.py
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

BASE_URL = 'http://www.kevinandbeanarchive.com/'
RSS_FILE = 'kevinandbean_podcast.xml'
#INCLUDE_YEARS = ["2015", "2016"]  # Add the years you want to include as strings
INCLUDE_YEARS = []  # Add the years you want to include as strings

# 1. Scrape the website for mp3 links
def get_mp3_links(url):
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, 'html.parser')
    links = set()
    excluded = []
    missing_year = []
    excluded_year = []
    # Accept both dash and underscore after date, and match .mp3 or .MP3 (case-insensitive)
    pattern = re.compile(r'^[A-Za-z]+_\d{1,2}_(\d{4})[-_]no_songs_no_commercials\.mp3$', re.IGNORECASE)
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.lower().endswith('.mp3'):
            filename = href.split('/')[-1]
            match = pattern.match(filename)
            if match:
                year = match.group(1)
                # If INCLUDE_YEARS is empty, include all years
                if not INCLUDE_YEARS or year in INCLUDE_YEARS:
                    if not href.startswith('http'):
                        href = BASE_URL + href.lstrip('/')
                    links.add(href)
                else:
                    excluded_year.append(filename)
            else:
                # Log files missing the year (e.g., June_09-no_songs_no_commercials.mp3)
                if re.match(r'^[A-Za-z]+_\d{2}[-_]no_songs_no_commercials\.mp3$', filename, re.IGNORECASE):
                    missing_year.append(filename)
                else:
                    excluded.append(filename)
    return sorted(links), excluded, missing_year, excluded_year

# 2. Generate RSS feed XML
def make_rss(mp3_links, year=None):
    items = []
    for link in mp3_links:
        filename = link.split('/')[-1]
        # Get mp3 size in bytes
        try:
            head = requests.head(link, allow_redirects=True, timeout=10)
            size_bytes = head.headers.get('Content-Length', '0')
        except Exception:
            size_bytes = '0'
        # Accept both dash and underscore after date, and single/double digit day
        date_match = re.match(r'^([A-Za-z]+)_(\d{1,2})_(\d{4})[-_]no_songs_no_commercials\.mp3$', filename, re.IGNORECASE)
        if date_match:
            month, day, year_str = date_match.groups()
            try:
                date_obj = datetime.strptime(f'{month} {day} {year_str}', '%B %d %Y')
                pubdate = date_obj.strftime('%a, %d %b %Y 08:00:00 GMT')
                season = year_str
                title = date_obj.strftime('%B %d, %Y') + ' &#124; The Kevin &amp; Bean Show'
            except Exception:
                date_obj = None
                pubdate = ''
                season = ''
                title = filename.replace('.mp3', '').replace('_', ' ').replace('-', ' ') + ' &#124; The Kevin &amp; Bean Show'
        else:
            date_obj = None
            pubdate = ''
            season = ''
            title = filename.replace('.mp3', '').replace('_', ' ').replace('-', ' ') + ' &#124; The Kevin &amp; Bean Show'
        guid = filename.replace('.mp3', '')
        items.append({
            'date_obj': date_obj,
            'xml': f'''\n    <item>\n      <title>{title}</title>\n      <enclosure url="{link}" length="{size_bytes}" type="audio/mpeg"/>\n      <guid>{guid}</guid>\n      <pubDate>{pubdate}</pubDate>\n      <itunes:season>{season}</itunes:season>\n    </item>'''
        })
    # Sort items by date_obj (None goes last)
    items.sort(key=lambda x: (x['date_obj'] is None, x['date_obj']))
    rss_items = ''.join([item['xml'] for item in items])
    if year:
        title = f'The Kevin &amp; Bean Archive - {year}'
        desc = f'The Kevin &amp; Bean Show {year} podcast from www.kevinandbeanarchive.com'
    else:
        title = 'The Kevin &amp; Bean Archive'
        desc = 'The Kevin &amp; Bean Show podcast from www.kevinandbeanarchive.com'
    rss = f'''<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"\n     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">\n  <channel>\n    <title>{title}</title>\n    <link>{BASE_URL}</link>\n    <description>{desc}</description>\n    <language>en-us</language>\n    <itunes:author>Kevin S.</itunes:author>\n    <itunes:category text="Comedy"/>\n    <itunes:image href="https://is1-ssl.mzstatic.com/image/thumb/Podcasts113/v4/e4/5d/9c/e45d9c4f-872c-0b84-d342-13898dbf331f/mza_3255451433259962360.jpg/1200x1200bf-60.jpg"/>\n    <itunes:explicit>no</itunes:explicit>\n    {rss_items}\n  </channel>\n</rss>'''
    return rss

def main():
    print('Scraping for mp3 links...')
    mp3_links, excluded, missing_year, excluded_year = get_mp3_links(BASE_URL)
    print(f'Found {len(mp3_links)} valid mp3 files.')
    print(f'Excluded {len(excluded)} files.')
    print(f'Files missing year: {len(missing_year)}')
    print(f'Files excluded based on year: {len(excluded_year)}')
    # Write excluded files to exclude.txt
    with open('exclude.txt', 'w', encoding='utf-8') as excl:
        for fname in excluded:
            excl.write(fname + '\n')
    # Write missing year files to exclude_missing_year.txt
    with open('exclude_missing_year.txt', 'w', encoding='utf-8') as excl_year:
        for fname in missing_year:
            excl_year.write(fname + '\n')
    # Write files excluded based on year to excludeBasedOnYear.txt
    with open('excludeBasedOnYear.txt', 'w', encoding='utf-8') as excl_year:
        for fname in excluded_year:
            excl_year.write(fname + '\n')
    # Group mp3_links by year
    mp3_by_year = {}
    pattern = re.compile(r'^[A-Za-z]+_\d{1,2}_(\d{4})[-_]no_songs_no_commercials\.mp3$', re.IGNORECASE)
    for link in mp3_links:
        filename = link.split('/')[-1]
        match = pattern.match(filename)
        if match:
            year = match.group(1)
            mp3_by_year.setdefault(year, []).append(link)
    # Generate a separate XML for each year
    for year, links in mp3_by_year.items():
        print(f'Generating RSS feed for {year}...')
        rss = make_rss(links, year)
        xml_name = f'kevinandbean_{year}.xml'
        with open(xml_name, 'w', encoding='utf-8') as f:
            f.write(rss)
        print(f'RSS feed written to {xml_name}')
    # Optionally, still generate the combined XML
    print('Generating combined RSS feed...')
    rss = make_rss(mp3_links)
    with open(RSS_FILE, 'w', encoding='utf-8') as f:
        f.write(rss)
    print(f'Combined RSS feed written to {RSS_FILE}')

if __name__ == '__main__':
    main()
