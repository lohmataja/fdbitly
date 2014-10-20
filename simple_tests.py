__author__ = 'Liuda'
from main import *


def tests():
    # testing adding urls
    my_urls = [c * (i + 1) for i, c in enumerate('abcdefg')]
    my_shorts = list('BCDEFGH')
    my_dict = {k: v.encode() for k, v in zip(my_shorts, my_urls)}
    #not in db
    for url in my_urls:
        assert db[urls.pack((url,))] == None
    #add urls
    for url in my_urls:
        add_url(db, url, '')
    #check that they are in db, associated with right values in urls and stats
    assert bytes_to_int(db[shortener.pack(('counter',))]) == len(my_shorts)
    for short in my_shorts:
        assert db[urls.pack((short,))] == my_dict[short]
        assert find_stats(db, short) == 0
    #check counting stats
    for i, short in enumerate(my_shorts):
        for j in range(i):
            lookup(db, short)
    for i, short in enumerate(my_shorts):
        assert find_stats(db, short) == i
    assert find_popular(db) == (len(my_shorts) - 1, [my_shorts[-1]])


tests()