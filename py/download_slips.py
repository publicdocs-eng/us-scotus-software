#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Copyright (c) 2016 the authors of the https://github.com/publicdocs project.
# Use of this file is subject to the NOTICE file in the root of the repository.
#


import requests
import json
import urllib2
import urllib
import hashlib
import os
import gzip
import codecs
import zlib
import argparse
import shutil
import StringIO
import time
import zipfile

from xml.sax.saxutils import escape
from xml.etree import ElementTree
from string import Template
from collections import namedtuple
from multiprocessing import Pool

def file_safe_uslm_id(cid):
    cid = cid.replace(u'/', u'_').replace(u':', u'_').replace(u'*', u'_').replace(u'$', u'_')
    if u"/" in cid:
        print u"(FATAL) #### Cannot have '/' in identifier " + cid
        assert(False)
        sys.exit(2)
        return
    if u".." == cid or u"/../" == cid or u"/.." in cid or u"../" in cid:
        print u"(FATAL) #### Cannot have '..' in identifier " + cid
        assert(False)
        sys.exit(2)
        return
    return cid


def prep_output(wd):
    wdir = wd + '/'
    if os.path.exists(wdir):
        shutil.rmtree(wdir)
    os.makedirs(wdir)

def handle(jsonfn, wd, ua):
    f = open(jsonfn, 'rb')
    s=unicode(f.read().decode(u'utf-8'))
    js = json.loads(s)
    ua = {u'User-Agent': ua}
    for slip in js:
        if u'link' not in slip or not slip[u'link'] or u'docket' not in slip or not slip[u'docket']:
            print 'Skipping ' + repr(slip)
            continue
        link = slip[u'link']
        fn = file_safe_uslm_id(slip[u'docket'])
        r = requests.get('https://www.supremecourt.gov/' + link, headers=ua)
        with open(wd + '/docket_slip_opinion__' + fn + '.pdf', 'wb') as k:
            k.write(r.content)
        # The robots.txt says the crawl delay is one second, let's be
        # courteous and wait 2 seconds.
        time.sleep(2)


def main():
    parser = argparse.ArgumentParser(description='Processes SCOTUS Slip json lists.')
    parser.add_argument('--wd', '--working-dir', dest='working_directory', action='store',
                        default='working/',
                        help='working directory for temporary files generated by processing')
    parser.add_argument('--i', '--input', dest='input', action='store', type=str,
                        help='path to input json file')
    parser.add_argument('--ua', '--user-agent', dest='ua', action='store', type=str,
                        help='user-agent')

    args = parser.parse_args()
    if args.input:
        prep_output(args.working_directory)
        handle(args.input, args.working_directory, args.ua)
    else:
        print u"(FATAL) #### Could not determine operating mode"
        assert(False)

if __name__ == "__main__":
    main()
