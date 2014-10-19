__author__ = 'Liuda'
import unittest
import nose
from url_shortener import *

class TestFDB(unittest.TestCase):
    def setup(self):
        fdb.api_version(200)
        db = fdb.open()
        shortener = fdb.directory.create_or_open(db, ('test_shortener',))
        del db[shortener.range(())]
        urls = shortener['urls']
        stats = shortener['stats']
        reverse_stats = shortener['reverse']
        #initialize the counter for generating short urls
        db[shortener.pack(('counter',))] = int_to_bytes(1)
        #reserve urls for internal needs
        db[urls.pack(('stats',))] = b''

    def test_add_url_supply_short(self):
        self.assertEqual(db[urls.pack(('short',))], None)
        add_url(db, 'full_url', 'short')
        self.assertEqual(db[urls.pack(('short',))], b'full_url')

    def test_add_url_autogenerate(self):
        self.assertEqual(db[urls.pack(('B',))], None)
        add_url(db, 'first_no_short', '')
        add_url(db, 'second_no_short', '')
        self.assertEqual(db[urls.pack(('B',))], b'first_no_short')
        self.assertEqual(db[urls.pack(('C',))], b'second_no_short')

    def test_add_url_dupl(self):
        add_url(db, 'full_url', 'short')
        self.assertEqual(db[urls.pack(('short',))], b'full_url')
        with self.assertRaises(KeyError):
            add_url(db, 'full_url', 'short')

    def test_stats_reserved(self):
        self.assertTrue(db[urls.pack(('stats',))].present())
        self.assertTrue(db[urls.pack(('stats',))] != None)

    def test_add_url_reserved(self):
        with self.assertRaises(KeyError):
            add_url(db, 'full_url', 'stats')

    def tearDown(self):
        del db[shortener.range(())]

# nose.run()