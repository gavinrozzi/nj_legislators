from pupa.scrape import Jurisdiction, Organization

from openstates.utils import url_xpath
from .bills import NJBillScraper
# from .events import NJEventScraper
from .people import NJPersonScraper
from .committees import NJCommitteeScraper

# don't retry- if a file isn't on FTP just let it go
settings = dict(SCRAPELIB_RETRY_ATTEMPTS=0)


class NewJersey(Jurisdiction):
    division_id = "ocd-division/country:us/state:nj"
    classification = "government"
    name = "New Jersey"
    url = "http://www.njleg.state.nj.us/"
    scrapers = {
        'bills': NJBillScraper,
        # 'events': NJEventScraper,
        'people': NJPersonScraper,
        'committees': NJCommitteeScraper,
    }
    parties = [
        {'name': 'Republican'},
        {'name': 'Democratic'}
    ]
    legislative_sessions = [
        {
            "_scraped_name": "2008-2009",
            "identifier": "213",
            "name": "2008-2009 Regular Session",
            "start_date": "2008-01-12"
        },
        {
            "_scraped_name": "2010-2011",
            "identifier": "214",
            "name": "2010-2011 Regular Session",
            "start_date": "2010-01-12"
        },
        {
            "_scraped_name": "2012-2013",
            "identifier": "215",
            "name": "2012-2013 Regular Session",
            "start_date": "2012-01-10"
        },
        {
            "_scraped_name": "2014-2015",
            "identifier": "216",
            "name": "2014-2015 Regular Session",
            "start_date": "2014-01-15"
        },
        {
            "_scraped_name": "2016-2017",
            "identifier": "217",
            "name": "2016-2017 Regular Session",
            "start_date": "2016-01-12",
            "end_date": "2018-01-09"
        },
        {
            "_scraped_name": "2018-2019",
            "identifier": "218",
            "name": "2018-2019 Regular Session",
            "start_date": "2018-01-08",
            "end_date": "2019-01-09"
        },
    ]
    ignored_scraped_sessions = [
        "2006-2007",
        "2004-2005",
        "2002-2003",
        "2000-2001",
        "1998-1999",
        "1996-1997"
    ]

    def get_organizations(self):
        legislature_name = "New Jersey Legislature"
        lower_chamber_name = "Assembly"
        lower_seats = 40
        lower_title = "Assembly Member"
        upper_chamber_name = "Senate"
        upper_seats = 40
        upper_title = "Senator"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        executive = Organization(name='Governor of New Jersey',
                                 classification="executive")
        upper = Organization(upper_chamber_name, classification='upper',
                             parent_id=legislature._id)
        lower = Organization(lower_chamber_name, classification='lower',
                             parent_id=legislature._id)

        for n in range(1, upper_seats + 1):
            upper.add_post(
                label=str(n), role=upper_title,
                division_id='{}/sldu:{}'.format(self.division_id, n))
        for n in range(1, lower_seats + 1):
            lower.add_post(
                label=str(n), role=lower_title,
                division_id='{}/sldl:{}'.format(self.division_id, n))

        yield legislature
        yield executive
        yield upper
        yield lower

    def get_session_list(self):
        return url_xpath('http://www.njleg.state.nj.us/',
'//select[@name="DBNAME"]/option/text()')






# This is a template for a Python scraper on morph.io (https://morph.io)
# including some code snippets below that you should find helpful

# import scraperwiki
# import lxml.html
#
# # Read in a page
# html = scraperwiki.scrape("http://foo.com")
#
# # Find something on the page using css selectors
# root = lxml.html.fromstring(html)
# root.cssselect("div[align='left']")
#
# # Write out to the sqlite database using scraperwiki library
# scraperwiki.sqlite.save(unique_keys=['name'], data={"name": "susan", "occupation": "software developer"})
#
# # An arbitrary query against the database
# scraperwiki.sql.select("* from data where 'name'='peter'")

# You don't have to do things with the ScraperWiki and lxml libraries.
# You can use whatever libraries you want: https://morph.io/documentation/python
# All that matters is that your final data is written to an SQLite database
# called "data.sqlite" in the current working directory which has at least a table
# called "data".



import unicodedata
from pupa.scrape import Scraper, Person
from .utils import MDBMixin


class NJPersonScraper(Scraper, MDBMixin):
    def scrape(self, session=None):
        if not session:
            session = self.jurisdiction.legislative_sessions[-1]['name']
            self.info('no session specified, using %s', session)

        year_abr = session[0:4]

        self._init_mdb(year_abr)

        roster_csv = self.access_to_csv('Roster')
        bio_csv = self.access_to_csv('LegBio')

        photos = {}
        for rec in bio_csv:
            photos[rec['Roster Key']] = rec['URLPicture']

        for rec in roster_csv:
            first_name = rec["Firstname"]
            middle_name = rec["MidName"]
            last_name = rec["LastName"]
            suffix = rec["Suffix"]
            full_name = first_name + " " + middle_name + " " + last_name + " " + suffix
            full_name = full_name.replace('  ', ' ')
            full_name = full_name[0: len(full_name) - 1]

            district = str(int(rec["District"]))
            party = rec["Party"]
            if party == 'R':
                party = "Republican"
            elif party == 'D':
                party = "Democratic"
            else:
                party = party
            chamber = rec["House"]
            if chamber == 'A':
                chamber = "lower"
            elif chamber == 'S':
                chamber = "upper"

            leg_status = rec["LegStatus"]
            # skip Deceased/Retired members
            if leg_status != 'Active':
                continue
            phone = rec["Phone"] or None
            email = None
            if rec["Email"]:
                email = rec["Email"]

            # Email has been removed from the Access DB, but it's
            # still AsmLAST@njleg.org and SenLAST@njleg.org - many
            # reps have these emails on their personal pages even if
            # they're gone from the DB file
            if not email:
                email = self._construct_email(chamber, rec['Sex'], last_name)

            try:
                photo_url = photos[rec['Roster Key']]
            except KeyError:
                photo_url = ''
                self.warning('no photo url for %s', rec['Roster Key'])
            url = ('http://www.njleg.state.nj.us/members/bio.asp?Leg=' +
                   str(int(rec['Roster Key'])))
            address = '{0}\n{1}, {2} {3}'.format(rec['Address'], rec['City'],
                                                 rec['State'], rec['Zipcode'])
            gender = {'M': 'Male', 'F': 'Female'}[rec['Sex']]

            person = Person(
                name=full_name,
                district=district,
                primary_org=chamber,
                party=party,
                image=photo_url,
                gender=gender,
            )

            person.add_link(url)
            person.add_source(url)
            person.add_source('http://www.njleg.state.nj.us/downloads.asp')

            person.add_contact_detail(type='address', value=address, note='District Office')
            if phone is not None:
                person.add_contact_detail(type='voice', value=phone, note='District Office')
            if email is not None:
                person.add_contact_detail(type='email', value=email, note='District Office')

            yield person

    def _construct_email(self, chamber, sex, last_name):
        # translate accents to non-accented versions for use in an
        # email and drop apostrophes and hyphens
        last_name = ''.join(c for c in
                            unicodedata.normalize('NFD', str(last_name))
                            if unicodedata.category(c) != 'Mn')
        last_name = last_name.replace("'", "").replace("-", "").replace(' ', '')
        sex_noun = {'M': 'm',
                    'F': 'w'}[sex]

        if chamber == 'lower':
            return 'As{}{}@njleg.org'.format(sex_noun, last_name)
        else:
return 'Sen' + last_name + '@njleg.org'

scraperwiki.sqlite.save(unique_keys=['person'], data={"name": "district", "party": "image"})

