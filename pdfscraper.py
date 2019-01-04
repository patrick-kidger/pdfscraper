import bs4
import contextlib
import itertools
import os
import re
import requests


def filesafe(str_):
    """Convert a string to something safe for filenames."""
    return "".join(c for c in str_ if c.isalnum() or c in (' ', '.', '_', '-')).rstrip()


def get(urls, verbose=False, download_endings=frozenset({'pdf', 'js', 'css', 'jpg', 'png', 'gif', 'woff2'})):
    """Saves a copy of all the webpages specified, in particular copying all pdfs all linked to on the webpage.
    
    It will download all linked files of types pdf, js, css, jpg, png, gif, woff2.
    
    Arguments:
        urls: an iterable of strings, each one a url. Each page linked will be copied, along with all of the files of
            the specified types.
        verbose: whether to list all files being downloaded. Defaults to False.
        download_endings: what kinds of linked files to download. Defaults to pdf, js, css, jpg, png, gif, woff2. Should
            be an iterable of strings.
    """

    download_endings = set(download_endings)  # just in case, in principle, a generator is passed.

    downloaded = set()

    # Go through all the links of things we need to download
    def should_download(href):
        if isinstance(href, str):
            return any(href.endswith('.' + end) for end in download_endings)
        return False
    
    reg = re.compile(r'^https?://[a-zA-Z0-9\.\-]*')
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:62.0) Gecko/20100101 Firefox/62.0'}
    for url in urls:
        if verbose:
            print(f'Getting {url}')
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
            
            # protocol specified, so should be an absolute reference
            if '//' in href:
                base_url = ''
            # not a protocol but starts with a /, so it should be a reference relative to the base directory of the
            # website
            elif href.startswith('/'):
                base_url = reg.findall(url)[0]
            # else it's a relative url
            # if there's a / (other than because of protocol specification) then we're in some subfolder, so discard
            # everything after the last slash
            elif '/' in url.replace('//', ''):
                base_url = url.rsplit('/', 1)[0] + '/'
            # else we're at the top of the site
            else:
                base_url = url + '/'

            abs_href = base_url + href

            if abs_href in downloaded:
                continue
            else:
                downloaded.add(abs_href)

            with open(os.path.join(os_url, subfolder, file_name), 'wb') as f:
                if verbose:
                    print(f'Getting {abs_href}')
                f.write(requests.get(abs_href, headers=headers).content)

        # Save the edited content
        html_filename = os.path.join(os_url, filesafe(title_tag.string) + '.html')
        with open(html_filename, 'w') as f:
            f.write(repr(soup))
