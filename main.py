"""
Url shortener.
/index      links to shorten_url, display_stats
/shorten    form to add a url to be shortened; optional field to come up with your own alias
            If alias is already in use, the user is offered to create a different alias.
            If no alias is provided, a random alias is generated.
            Redirects to the page displaying the full url and the alias that has been just recorded.
/stats      displays 5 most popular short urls and 5 least popular short urls.
/<short_url>    displays how many times this url has been access and redirects to the full url
                displays error if short_url is not found
"""

from flask import request, render_template, Flask, redirect
app = Flask(__name__)
from wtforms import Form, StringField, validators

import fdb
import struct
import re
HOME_URL='http://127.0.0.1:5000/'


def int_to_base64(n):
    """
    Encodes integers > 0 in a url-safe, base 64 (NOT rfc3548) encoding.
    """
    alph = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
    res = ''
    while n > 0:
        next_c = alph[n % 64]
        n //= 64
        res = next_c + res
    return res


def bytes_to_int(b):
    if type(b) != bytes:
        b = b.value
    return struct.unpack('>I', b)[0]


def int_to_bytes(n):
    return struct.pack('>I', n)

#initialize the database
fdb.api_version(200)
db = fdb.open()
shortener = fdb.directory.create_or_open(db, ('shortener',))
# del db[shortener.range(())]
urls = shortener['urls']
stats = shortener['stats']
reverse_stats = shortener['reverse']
#initialize the counter for generating short urls
db[shortener.pack(('counter',))] = int_to_bytes(1)
#reserve urls for internal needs
db[urls.pack(('stats',))] = b''

@fdb.transactional
def add_url(tr, full_url, short_url):
    """
    Adds an entry for short_url as key and full_url as value to the database, and initializes the statistics entries
    associated with this short url. If short_url is not supplied, autogenerates a short url.
    Returns the short url.
    If the short_url is already in use, raises an exception.
    """
    if short_url == '':
        current_count = bytes_to_int(tr[shortener.pack(('counter',))])
        while tr[urls.pack((int_to_base64(current_count),))].present():
            current_count += 1
        short_url = int_to_base64(current_count)
        tr[shortener.pack(('counter',))] = int_to_bytes(current_count)
    elif tr[urls.pack((short_url,))].present():
        raise KeyError("Url already in use")
    # add url to the db
    tr[urls.pack((short_url,))] = full_url.encode()
    # init the stats
    tr[stats.pack((short_url,))] = int_to_bytes(0)
    tr[reverse_stats.pack((0, short_url))] = b''
    return short_url


@fdb.transactional
def lookup(tr, short_url):
    """
    Takes a short_url and returns the full_url associated with it. If short_url is not found, raises an exception.
    """
    full_url = tr[urls.pack((short_url,))]
    if full_url == None:
        raise KeyError
    update_stats(tr, short_url)
    return full_url


@fdb.transactional
def update_stats(tr, url):
    """
    Updates statistics associated with the url in the database: increments the counter in stats and reverse_stats
    of the times url has been accessed.
    """
    url_key = stats.pack((url,))
    val = bytes_to_int(tr[url_key])
    tr[url_key] = int_to_bytes(val + 1)
    del tr[reverse_stats.pack((val, url))]  # delete the previous value
    tr[reverse_stats.pack((val + 1, url))] = b''  # put in new value


@fdb.transactional
def find_popular(tr, most=True):
    """
    If most is set to True, returns most popular urls; if it is set to False, least popular ones.
    Returns the number of times the urls have been accessed and the list of the urls.
    """
    r = reverse_stats.range()
    max_record = tr.get_range(r.start, r.stop, limit=1, reverse=most).to_list()[0]
    max_value = reverse_stats.unpack(max_record.key)[0]
    elements = [reverse_stats.unpack(el.key)[1] for el in tr[reverse_stats.range((max_value,))]]
    return max_value, elements


@fdb.transactional
def print_sub(tr, sub):
    for item in tr[sub.range()]:
        key = sub.unpack(item.key)
        try:
            value = bytes_to_int(item.value)
        except struct.error:
            value = item.value
        print(key, value, sep='\t')


class ShortenerForm(Form):
    full_url = StringField('Enter the url you wish to shorten', [validators.DataRequired()])
    short_url = StringField('Enter desired short url')

@fdb.transactional
def find_stats(tr, url):
    times_accessed = tr[stats.pack((url,))]
    if times_accessed == None:
        raise KeyError("{} is not found".format(url))
    else:
        return bytes_to_int(times_accessed)

@app.route('/', methods=['GET', 'POST'])
def index():
    # return 'Hi'
    form = ShortenerForm(request.form)
    if request.method == 'POST' and form.validate():
        # get urls from the form
        short_url = form.short_url.data
        full_url = form.full_url.data
        if short_url != '' and not re.match('(\w|_|-)+$', short_url):
            return render_template("invalid_short_url.html", form=form)
        try:
            short_url = add_url(db, full_url, short_url)
        except KeyError:
            return render_template("try_again.html", form=form)
        short_url_to_display = HOME_URL + short_url
        # return short_url_to_display + ' ' + full_url_to_display
        return """Original url: <a href="{}"> {} </a> <br>
                Short url: <a href="{}"> {} </a> <br>
                <hr>
                <a href="{}"> Add another url. </a> <br>
                <a href="{}"> See most popular urls. </a> """.format(full_url, full_url,
                                                                   short_url_to_display, short_url_to_display,
                                                                   HOME_URL,
                                                                   HOME_URL+'stats')
    return render_template('shorten.html', form=form)


@app.route('/<short_url>')
def short_to_full(short_url):
    try:
        full_url = lookup(db, short_url)
    except KeyError:
        return render_template('page_not_found.html'), 404
    return redirect(full_url, code=302)

@app.route('/stats/')
@app.route('/stats/<url>')
def show_stats(url=''):
    if url == '':
        times_accessed, popular_urls = find_popular(db, most=True)
        return ("Most popular short urls (accessed {} times):<br>".format(times_accessed) +
                '<br>'.join(['<a href="{}{}">{}{}</a>'.format(HOME_URL, url, HOME_URL, url) for url in popular_urls])
                + '<br>')
    else:
        try:
            times_accessed = find_stats(db, url)
        except KeyError as e:
            return render_template('page_not_found.html'), 404
        return "{} was accessed {} times.".format(url, times_accessed)

if __name__ == '__main__':
    app.run()
