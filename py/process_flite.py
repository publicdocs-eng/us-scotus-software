#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Copyright (c) 2016 the authors of the https://github.com/publicdocs project.
# Use of this file is subject to the NOTICE file in the root of the repository.
#

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
import zipfile

from xml.sax.saxutils import escape
from xml.etree import ElementTree
from string import Template
from collections import namedtuple
from multiprocessing import Pool

## CONSTANTS

_out_header_markdown = Template(u"""---
---

# $fancytitle

* Use of this file is subject to the NOTICE at https://github.com/publicdocs/notice/blob/master/NOTICE
* See the [Document Metadata](${docmd}) for more information.
  This file is generated from historical government data; content and/or formatting may be inaccurate and out-of-date and should not be used for official purposes.

----------
----------

$innercontent


----------
----------

""")


NBSP = u"\u00A0"

## STRUCTURES
ZipContents = namedtuple("ZipContents", "sha512 titledir")
ProcessedElement = namedtuple("ProcessedElement", "inputmeta outputmd tail")
FileDelimiter = namedtuple("FileDelimiter", "identifier dir titleroot reporoot prev next filename uslmid")
FileDelimiter.__new__.__defaults__ = (None, ) * len(FileDelimiter._fields)
Link = namedtuple("Link", "refcontent href")


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

# No links, images, or html tags. Don't auto bold or italics either
_md_escape_chars = list(u'\\`_{}[]<>*_')
def md_escape(txt):
    ret = u""
    for c in txt:
        if c in _md_escape_chars:
            ret = ret + "\\"
        ret = ret + c
    return ret


def process_zip(input_zip, wd):
    wdir = wd + '/unzipped'
    if os.path.exists(wdir):
        shutil.rmtree(wdir)
    os.makedirs(wdir)
    file_content = u''
    with gzip.open(input_zip, 'rb') as f:
        file_content = f.read()
    return unicode(file_content.decode('utf-8')).splitlines()

def prep_output(wd):
    wdir = wd + '/gen'
    if os.path.exists(wdir):
        shutil.rmtree(wdir)
    os.makedirs(wdir)

_quotes = {'"': "&quot;", "'": "&apos;"}
def html_escape(t):
    return escape(t, _quotes)


def delete_line(path1, path2, num):
    fr = codecs.open(path1, 'rb', encoding='utf-8')
    fw = codecs.open(path2, 'wb', encoding='utf-8')
    i = 1
    for line in fr:
        if i == num:
            fw.write(u'\n')
        else:
            fw.write(line)
        i = i + 1
    fr.close()
    fw.close()

def replace_line(path1, path2, a1, a2):
    fr = codecs.open(path1, 'rb', encoding='utf-8')
    fw = codecs.open(path2, 'wb', encoding='utf-8')
    i = 1
    for line in fr:
        if line == a1:
            fw.write(a2)
        else:
            fw.write(line)
        i = i + 1
    fr.close()
    fw.close()

def process_lines(contents, wd):
    wdir = wd + '/gen/cases/'
    if os.path.exists(wdir):
        shutil.rmtree(wdir)
    os.makedirs(wdir)

    readylines = []
    for l in contents:
        if l == u'================== BEGIN ORIGINAL DATA ==================':
            readylines = []
            continue
        elif l == u'..END :':
            outlines = []
            lastsp = False
            lastl = u''
            for z in readylines:
                if (not z) or (not z.strip()):
                    continue
                if lastl:
                    lastl = lastl + u' ' + z.strip()
                else:
                    lastl = z.strip()
                if z.endswith(u' '):
                    # THis is how they encode paragraph breaks!
                    outlines.append(lastl.strip())
                    lastl = u''
            if lastl and lastl.strip():
                outlines.append(lastl.strip())
                lastl = u''
            casename = outlines[0]
            comps = casename.split(u' ')
            casevol = comps[-3]
            if casevol.startswith(u'U'):
                casevol = comps[-4]
            if casevol.endswith(u','):
                casevol = casevol[:-1]
            casenum = comps[-1]
            if not os.path.exists(wdir + u'/' + casevol):
                os.makedirs(wdir + u'/' + casevol)
            innercontent = md_escape(u'\n\n'.join(outlines))
            of = wdir + u'/' + casevol + u'/' + file_safe_uslm_id(casename[:64]) + u'.md'
            fc = _out_header_markdown.substitute(
                    docmd = '',
                    innercontent = innercontent,
                    fancytitle = md_escape(casename),
            )
            f = open(of, 'w')
            f.write(fc.encode('utf8'))
            f.close()
            readylines = []
        else:
            readylines.append(l)

    print 'Finished ' + inc + ' cases.'

def main():
    parser = argparse.ArgumentParser(description='Processes FLITE SCOTUS files.')
    parser.add_argument('--wd', '--working-dir', dest='working_directory', action='store',
                        default='working/',
                        help='working directory for temporary files generated by processing')
    parser.add_argument('--i', '--input-gz', dest='input_gz', action='store', type=str,
                        help='path to input gz file')

    args = parser.parse_args()
    if args.input_gz:
        lines = process_zip(args.input_gz, args.working_directory)
        prep_output(args.working_directory)
        process_lines(lines, args.working_directory)
    else:
        print u"(FATAL) #### Could not determine operating mode"
        assert(False)

if __name__ == "__main__":
    main()
