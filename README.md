fdbitly
=======

Url shortener created using FDB API.

Design decisions.
======================

Generating a short url:
---------------------------
There is a number of ways to generate a short url. I chose the simplest one: keep track of a counter (integer), which is incremented every time it's used for generating a short url. The integer is then encoded using 64 symbols (alphanumerics, dash and underscore).
