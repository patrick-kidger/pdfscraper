import bs4
import contextlib
import itertools
import os
import re
import requests


def filesafe(str_):
    """Convert a string to something safe for filenames."""
    return "".join(c for c in str_ if c.isalnum() or c in (' ', '.', '_', '-')).rstrip()


def get(urls):
    reg = re.compile(r'^https?://.*?/')
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:62.0) Gecko/20100101 Firefox/62.0'}
    for url in urls:
        # Get the HTML
        content = requests.get(url, headers=headers).content
        soup = bs4.BeautifulSoup(content, 'html.parser')
        if soup.find('base'):
            raise Exception('Base tag found.')
        title_tag = soup.find('title')
        if not title_tag:
            raise Exception('No title tag')

        # Create the relevant folders
        os_url = filesafe(url)
        with contextlib.suppress(FileExistsError):
            os.mkdir(os_url)
        with contextlib.suppress(FileExistsError):
            os.mkdir(os.path.join(os_url, 'pdf'))
        with contextlib.suppress(FileExistsError):
            os.mkdir(os.path.join(os_url, 'data'))

        # Go through all the links of things we need to download
        def should_download(href):
            if isinstance(href, str):
                endings = {'pdf', 'js', 'css', 'jpg', 'png', 'gif', 'woff2'}
                return any(href.endswith('.' + end) for end in endings)
            return False
        links_href = [(tag, 'href') for tag in soup.find_all(attrs={'href': should_download})]
        links_src = [(tag, 'src') for tag in soup.find_all(attrs={'src': should_download})]
        for link, linktype in itertools.chain(links_href, links_src):
            # Change the current content to point to the downloaded stuff
            href = link.attrs[linktype]
            if href.endswith('.pdf'):
                subfolder = 'pdf'
            else:
                subfolder = 'data'
            file_name = filesafe(href.split('/')[-1])
            link.attrs[linktype] = subfolder + '/' + file_name
            # Download it
            if href.startswith('/'):
                base_url = reg.findall(url)[0]
            else:
                if href.rindex('.') > href.rindex('/'):
                    base_url = url.rsplit('/', 1)[0] + '/'
                else:
                    if url.endswith('/'):
                        base_url = url
                    else:
                        base_url = url + '/'
            abs_href = base_url + href
            with open(os.path.join(os_url, subfolder, file_name), 'wb') as f:
                f.write(requests.get(abs_href, headers=headers).content)

        # Save the edited content
        html_filename = os.path.join(os_url, filesafe(title_tag.string) + '.html')
        with open(html_filename, 'w') as f:
            f.write(repr(soup))


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        get(sys.argv[1:])
    else:
        get(input('Urls: ').split(' '))
