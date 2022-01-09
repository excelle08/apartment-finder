#!/usr/bin/env python3

from common import sess, MyHTMLParser
import getopt
import json
import sys

amenities_list = {
    'ac': ('Air Conditioning', 'air-conditioning'),
    'wd': ('In-unit Washer & Dryver', 'washer-dryer'),
    'wd-hookup': ('Washer & Dryer Hookups', 'washer_dryer-hookup'),
    'dishwasher': ('Dishwasher', 'dishwasher'),
    'wheelchair': ('Wheelchair Access', 'wheelchair-accessible'),
    'parking': ('Parking', 'parking'),
    'laundry': ('(Public) Laundry Facilities', 'laundry-facilities'),
    'fitness': ('Fitness Center', 'fitness-center'),
    'pool': ('Swimming Pool', 'pool'),
    'elevator': ('Elevator', 'elevator'),
    'furnished': ('Furnished', 'furnished'),
    'lofts': ('Lofts', 'lofts'),
    'gated': ('Gated', 'gated'),
    'fireplace': ('Fireplace', 'fireplace'),
    'patio': ('Patio', 'patio'),
    'garage': ('Garage', 'garage'),
    'hw-floors': ('Hardwood Floors', 'hardwood-floors'),
    'balcony': ('Balcony', 'balcony'),
    'office': ('Office', 'office'),
    'clubhouse': ('Clubhouse', 'clubhouse'),
    'biz-ctr': ('Business Center', 'business-center'),
    'ctrl-acc': ('Controlled Access', 'controlled-access'),
    'wic': ('Walk-in Closets', 'walk-in-closets')
}


class AptSearchPageParser(MyHTMLParser):

    def __init__(self):
        super(AptSearchPageParser, self).__init__()
        self.apartments = []

    def on_data(self, data):
        if len(self.tags) == 0:
            return
        toptag = self.tags[-1]
        if str(toptag) == 'script' and toptag.attr_eq('type', 'application/ld+json'):
            obj = json.loads(data)
            if isinstance(obj, list):
                for item in obj:
                    self.apartments.append(item)


def specs_bedrooms(specs, min_beds, max_beds, studio):
    if studio:
        specs.append('studios')
    elif isinstance(min_beds, int) and max_beds is None:
        specs.append('min-%d-bedrooms' % min_beds)
    elif min_beds is None and isinstance(max_beds, int):
        specs.append('max-%d-bedrooms' % max_beds)
    elif isinstance(min_beds, int) and isinstance(max_beds, int):
        if min_beds > max_beds:
            raise ValueError('minimum number of bedrooms is greater than maximum')
        specs.append('%d-to-%d-bedrooms' % (min_beds, max_beds))


def specs_rent(specs, min_rent, max_rent):
    if isinstance(min_rent, int) and max_rent is None:
        specs.append('over-%d' % min_rent)
    elif min_rent is None and isinstance(max_rent, int):
        specs.append('under-%d' % max_rent)
    elif isinstance(min_rent, int) and isinstance(max_rent, int):
        if min_rent > max_rent:
            raise ValueError('minimum rent is greater than maximum')
        specs.append('%d-to-%d' % (min_rent, max_rent))


def specs_pet_policy(specs, cat, dog):
    if cat and not dog:
        specs.append('pet-friendly-cat')
    elif not cat and dog:
        specs.append('pet-friendly-dog')
    elif cat and dog:
        specs.append('pet-friendly')


def apt_spec(min_beds=None, max_beds=None, studio=False, min_rent=None, max_rent=None, cat=False, dog=False):
    specs = []

    specs_bedrooms(specs, min_beds, max_beds, studio)
    specs_rent(specs, min_rent, max_rent)
    specs_pet_policy(specs, cat, dog)

    specstr = '-'.join(specs)
    if len(specstr) > 0:
        specstr = '/' + specstr
    return specstr


def apt_location(location):
    location = location.lstrip().rstrip().lower()
    location = location.replace(', ', '-').replace(' ', '-').replace(',', '-')
    return location


def apt_amenities(amenities):
    criteria = []
    for item in amenities:
        try:
            criteria.append(amenities_list[item][1])
        except KeyError:
            raise Exception('Not recognized amenity key: %s' % item)
    specstr = '-'.join(criteria)
    if len(specstr) > 0:
        specstr = '/' + specstr
    return specstr


def findval(obj, key, default=None):
    try:
        return obj[key]
    except KeyError:
        return default


def find_apartments(location, **kwargs):
    url = 'https://www.apartments.com/'
    url += apt_location(location)
    url += apt_spec(min_beds=findval(kwargs, 'min_beds'), max_beds=findval(kwargs, 'max_beds'),
        studio=findval(kwargs, 'studio', False), min_rent=findval(kwargs, 'min_rent'),
        max_rent=findval(kwargs, 'max_rent'), cat=findval(kwargs, 'cat', False),
        dog=findval(kwargs, 'dog', False)
    )
    url += apt_amenities(findval(kwargs, 'amenities', []))

    resp = sess.get(url)

    search_page_parser = AptSearchPageParser()
    search_page_parser.feed(resp.text)
    res = []
    for apt in search_page_parser.apartments:
        vloc, ploc = apt['location']
        addr = ploc['address']
        res.append({
            'name': ploc['name'],
            'url': vloc['url'],
            'street': addr['streetAddress'],
            'city': addr['addressLocality'],
            'state': addr['addressRegion'],
            'zipcode': addr['postalCode']
        })
    return res


def help():
    print('Usage: %s [filters...] <location>' % sys.argv[0])
    print('')
    print('Filters:')
    print('  -b, --min-beds <1-4>: Minimum number of bedrooms. (1-4)')
    print('  -B, --max-beds <1-3 | studio>: Maximum number of bedrooms. (1-3 or "studio")')
    print('  -r, --min-rent <N>: Minimum monthly rent')
    print('  -R, --max-rent <N>: Maximum monthly rent')
    print('  -c, --cat: Cat friendly')
    print('  -d, --dog: Dog friendly')
    print('  -a, --amenities <a,b,c...>: List of amenities required')
    print('    Recognized list of amenities:')
    for key, value in amenities_list.items():
        print('    %s - %s' % (key, value[0]))

if __name__ == '__main__':
    longargs = ['min-beds=', 'max-beds=', 'min-rent=', 'max-rent=', 'cat', 'dog', 'amenities=']
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'cdhb:B:r:R:a:', longargs)
    except getopt.GetoptError as e:
        print(e)
        help()
        exit(1)

    criteria = {}
    for k, v in opts:
        if k in ('-b', '--min-beds'):
            criteria['min_beds'] = int(v)
        elif k in ('-B', '--max-beds'):
            if v.lower() == 'studio':
                criteria['studio'] = True
            else:
                criteria['max_beds'] = int(v)
        elif k in ('-r', '--min-rent'):
            criteria['min_rent'] = int(v)
        elif k in ('-R', '--max-rent'):
            criteria['max_rent'] = int(v)
        elif k in ('-c', '--cat'):
            criteria['cat'] = True
        elif k in ('-d', '--dog'):
            criteria['dog'] = True
        elif k in ('-a', '--amenities'):
            criteria['amenities'] = v.split(',')
        elif k == '-h':
            help()
            exit(0)
        else:
            print('Unrecognized option %s' % k)
            help()
            exit(1)

    location = ' '.join(args)
    if not location:
        help()
        exit(1)

    apts = find_apartments(location, **criteria)
    for apt in apts:
        print(apt['name'])
        print(apt['street'])
        print('%s, %s, %s' % (apt['city'], apt['zipcode'], apt['state']))
        print(apt['url'])
        print('')

