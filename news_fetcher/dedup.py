processed_urls = set()

def is_processed(url):
    return url in processed_urls

def mark_processed(url):
    processed_urls.add(url)