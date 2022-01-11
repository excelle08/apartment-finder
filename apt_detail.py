#!/usr/bin/env python3

from bs4 import BeautifulSoup
from common import sess
from google import load_comments

import bs4
import json
import locale
import re
import sys

locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
datepat = re.compile(r'(Now|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Nov|Dec)(\w*\. \d+)?')
pricepat = re.compile('\$([0-9,]+)')


class ApartmentPage():

    def __init__(self, html_text, apt_summary):
        self.soup = BeautifulSoup(html_text.replace('–', '-'), 'html.parser')
        self.apt = apt_summary
        self._extract_apt_overall()
        self._extract_floor_plans()
        self._extract_description()
        self._extract_contact()
        self._extract_amenities()

    @staticmethod
    def _extract_price_range(text):
        prices = text.split(' - ')
        if len(prices) == 1:
            try:
                lower = upper = locale.atoi(prices[0].strip('$'))
            except ValueError:
                lower = upper = None
        else:
            lower = locale.atoi(prices[0].strip('$'))
            upper = locale.atoi(prices[1].strip('$'))
        return lower, upper

    @staticmethod
    def _extract_br_range(text):
        rooms = text.split(' - ')
        if rooms[0].lower() == 'studio':
            lower = 0
        else:
            lower = int(rooms[0][0])

        if len(rooms) > 1:
            upper = int(rooms[1][0])
        else:
            upper = lower
        return lower, upper

    @staticmethod
    def _extract_ba_range(text):
        baths = text.split(' - ')
        if len(baths) == 1:
            lower = upper = int(baths[0][0])
        else:
            lower = int(baths[0][0])
            upper = int(baths[1][0])
        return lower, upper

    @staticmethod
    def _extract_area_range(text):
        text = text.replace(' sq ft', '')
        areas = text.split(' - ')
        if len(areas) == 1:
            lower = upper = locale.atoi(areas[0])
        else:
            lower = locale.atoi(areas[0])
            upper = locale.atoi(areas[1])
        return lower, upper

    def _extract_apt_overall(self):
        container = self.soup.find_all('div', class_='priceBedRangeInfoInnerContainer')
        for item in container:
            infotype = item.find(class_='rentInfoLabel').text
            infoval = item.find(class_='rentInfoDetail').text
            if infotype == 'Monthly Rent':
                lower, upper = self._extract_price_range(infoval)
                self.apt['min_rent'] = lower
                self.apt['max_rent'] = upper
            elif infotype == 'Bedrooms':
                lower, upper = self._extract_br_range(infoval)
                self.apt['min_beds'] = lower
                self.apt['max_beds'] = upper
            elif infotype == 'Bathrooms':
                lower, upper = self._extract_ba_range(infoval)
                self.apt['min_baths'] = lower
                self.apt['max_baths'] = upper
            elif infotype == 'Square Feet':
                lower, upper = self._extract_area_range(infoval)
                self.apt['min_area_sqft'] = lower
                self.apt['max_area_sqft'] = upper

    @staticmethod
    def _extract_model_summary(model):
        """model: a '<div>' node with class attribute equal to 'pricingGridItem'"""
        desc = {}
        # name
        desc['name'] = model.find('span', class_='modelName').text
        # rent range
        rent_label = model.find('span', class_='rentLabel').text.strip('\r\n ')
        lower, upper = ApartmentPage._extract_price_range(rent_label)
        desc['min_rent'] = lower
        desc['max_rent'] = upper
        return desc

    @staticmethod
    def _extract_model_bed_baths(model):
        """model: a '<div>' node with class attribute equal to 'pricingGridItem'"""
        desc = {}
        specs = model.find('span', class_='detailsTextWrapper').find_all('span')
        for spec in specs:
            if spec.text.endswith('beds'):
                desc['beds'] = int(spec.text.split(' ')[0])
            elif spec.text.lower() == 'studio':
                desc['beds'] = 0
            elif spec.text.endswith('baths'):
                desc['baths'] = int(spec.text.split(' ')[0])
            elif spec.text.endswith('sq ft'):
                lower, upper = ApartmentPage._extract_area_range(spec.text)
                desc['min_area_sqft'] = lower
                desc['max_area_sqft'] = upper
        return desc

    @staticmethod
    def _extract_model_avail_units(model):
        unit_nodes = model.find_all('li', class_='unitContainer')
        units = []
        for u in unit_nodes:
            unit_name = u.find('div', class_='unitColumn').text.strip('\r\n ')
            pricestr = u.find('div', class_='pricingColumn').text
            unit_price = locale.atoi(pricepat.search(pricestr).group(1))
            datestr = u.find('span', class_='dateAvailable').text
            avail = datepat.search(datestr).group(0)
            units.append({
                'unit': unit_name,
                'price': unit_price,
                'date_available': avail
            })
        return units

    def _extract_floor_plans(self):
        self.apt['floorplans'] = []
        models = self.soup.find_all('div', class_='pricingGridItem')
        for model in models:
            model_desc = self._extract_model_summary(model)
            # bed, bath and area
            bed_baths = self._extract_model_bed_baths(model)
            model_desc.update(bed_baths)
            # features and amenities
            model_desc['amenities'] = []
            amenities = model.find_all('span', class_='amenity')
            for am in amenities:
                model_desc['amenities'].append(am.text)
            # leasing info
            leasing = model.find('span', class_='leaseDepositLabel').find_all('span')
            model_desc['leasing_term'] = leasing[0].text
            model_desc['deposit'] = leasing[1].text
            # availability
            date_avail = model.find('span', class_='availabilityInfo')
            model_desc['date_available'] = date_avail.text if date_avail is not None else None
            # available units, if listed
            model_desc['units'] = self._extract_model_avail_units(model)
            self.apt['floorplans'].append(model_desc)

    def _extract_description(self):
        desc = self.soup.find('section', class_='descriptionSection')
        if not desc:
            return
        # about text
        about = []
        for paragraph in desc.find_all('p'):
            about.append(paragraph.text)
        self.apt['about'] = about
        # unique features
        features = []
        for feat in desc.find_all('li', class_='uniqueAmenity'):
            features.append(feat.span.text)
        self.apt['features'] = features

    def _extract_contact(self):
        contact = self.soup.find('section', id='officeHoursSection')
        if not contact:
            return
        phone_node = contact.find('div', class_='phoneNumber')
        self.apt['tel'] = phone_node.a.span.text
        website = contact.find('a', class_='propertyWebsiteLink')
        self.apt['website'] = website['href']

    def _get_amenities_of_a_category(self, category):
        """category: an <h2> title node"""
        amenities = []
        for sib in category.next_siblings:
            if not isinstance(sib, bs4.element.Tag):
                continue
            if sib.name == 'h2':
                break
            if sib.name == 'div' and 'spec' in sib['class']:
                specs = sib.find_all('li', class_='specInfo')
                amenities.extend([s.span.text for s in specs])
        return amenities

    def _extract_amenities(self):
        amenities = {}
        amenity_section = self.soup.find('section', class_='amenitiesSection')
        categories = amenity_section.find_all('h2', class_='sectionTitle')
        for cat in categories:
            title = cat.text
            amenities[title] = self._get_amenities_of_a_category(cat)
        self.apt['amenities'] = amenities

    def __getattr__(self, key):
        if key not in self.apt:
            return None
        return self.apt[key]

    def __getitem__(self, key):
        if key not in self.apt:
            return None
        return self.apt[key]


if __name__ == '__main__':
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = 'https://www.apartments.com/elan-menlo-park-menlo-park-ca/9yntwg4/'

    resp = sess.get(url)
    apt_detail = ApartmentPage(resp.text, {})
    print(json.dumps(apt_detail.apt, indent=2))
