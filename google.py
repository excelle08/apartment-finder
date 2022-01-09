#!/usr/bin/env python3

from common import sess
import json
import re
import sys

fid_pattern = re.compile(r'data\-fid\=\"([0-9a-fx:]+)\"')


def search(keyword):
    resp = sess.get(url='https://google.com/search?q=' + keyword)
    return resp.text


def extract_feature_id(body):
    match = fid_pattern.search(body)
    if match is None:
        return None
    return match.group(1)


def load_comments(fid, **kwargs):
    query = {
        'feature_id': fid,
        'review_source': 'All reviews',
        'sort_by': 'qualityScore',
        'is_owner': 'false',
        'filter_text': '',
        'associated_topic': '',
        'next_page_token': '',
        'async_id_prefix': '',
        '_pms': 's',
        '_fmt': 'json'
    }
    # Overrided parameters from caller's args
    for k, v in kwargs.items():
        query[k] = v
    # Compose the `async=` query string
    params = []
    for k, v in query.items():
        params.append('%s:%s' % (k, v))
    params_str = ','.join(params)
    # Send request
    resp = sess.get(url='https://www.google.com/async/reviewDialog?async=' + params_str)
    resp_json_text = resp.text[5:]
    reviews_obj = json.loads(resp_json_text)
    if 'other_user_review' not in reviews_obj['localReviewsDialogProto']['reviews']:
        return [], ''

    reviews = reviews_obj['localReviewsDialogProto']['reviews']['other_user_review']
    next_page = reviews_obj['localReviewsDialogProto']['reviews']['next_page_token']
    return reviews, next_page


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Please include some keywords.')
        exit(1)

    keywords = ' '.join(sys.argv[1:])
    search_result = search(keywords)
    fid = extract_feature_id(search_result)
    if fid is None:
        print('No feature id found.')
        exit(0)

    all_reviews = []
    next_page = ''
    while True:
        reviews, next_page = load_comments(fid, next_page_token=next_page)
        all_reviews.extend(reviews)
        if not next_page:
            break

    if len(all_reviews) == 0:
        print('No reviews available.')
        exit(0)

    count = 1
    for r in all_reviews:
        if 'review_text' not in r:
            continue
        print('#%d' % count)
        print('Reviewer: ' + r['author_real_name'])
        print('Rating: %d' % r['star_rating']['value'])
        print('Time: ' + r['publish_date']['localized_date'])
        print('Comment: ' + r['review_text']['full_html'])
        print('')
        count += 1

