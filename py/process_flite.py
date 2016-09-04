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
import re
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


## BEGIN ==
## These regular expressions are possibly modified/adapted versions originally from:
## https://github.com/usgpo/collections/blob/master/CHRG/CHRG-RegEx.md

decimalsT = "ten|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety"
teensT = "eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen"
numbers1T = "one|two|three|four|five|six|seven|eight|nine"
ordinals1T = "first|second|third|fourth|fifth|sixth|seventh|eighth|ninth"
ordinals2T = "(?:" + teensT + ")th"
ordinals3T = "(?:" + decimalsT + ")th"
ordinals4T = "(?:" + decimalsT + ")-(?:" + ordinals1T + ")"
ordinalsT = ordinals1T + "|" + ordinals2T + "|" + ordinals3T + "|" + ordinals4T


lawContentP = re.compile(
"(\\b(?:Public|Private|Pub|Priv|Pvt|P)\\.*\\s*(?:Law|L|R)\\.*)\\s*(?:No\\.)?\\s*(\\d+)[-\\xAD]+\\s*(\\d+)",
   re.IGNORECASE | re.MULTILINE)

publicLawContentP = re.compile(
"(\\b(?:Public|Pub|P)\\.*\\s*(?:Laws?|L|R)\\.*)\\s*(?:Nos?\\.?|Numbers?)?\\s*(?P<pl_p1>\\d+)[-\\xAD]+\\s*(?P<pl_p2>\\d+)",
   re.IGNORECASE | re.MULTILINE)

multiLawContentP = re.compile(
"(\\b(?:Public|Private|Pub|Priv|Pvt)\\.?\\s*(?:Laws|L)\\.?)\\s*(?:Nos?\\.|Numbers?)?(\\s*\\d+[-\\xAD]+\\s*\\d+(?:\\b\\d+[-\\xAD]+\\s*\\d+|,|and|\\s+)+)",
   re.IGNORECASE | re.MULTILINE)

uscT ="U\\.?\\s*S\\.?\\s*C(?:\\.|ode)?\\s*"
postAUscT ="app\\.|Appendix"
singleSectionNoCaptureRegex ="\\d[a-z0-9-]*\\b(?:\\([a-z0-9]+\\))*(?:\\s+note|\\s+et seq\\.?)?"
singleChapterNoCaptureRegex = "\\d[a-z0-9-]*\\b"

## Matches following formats: chapter 8 of title 212, United States Code
## Section 1477 of title 10, United States Code

usCodeLargeP = re.compile(
   "(?:sections?\\s*(\\w+)\\s*(?:of\\s*))?CHAPTERS?\\s*(\\d+[a-z]*) of title (\\d+),\\s*UNITED\\s*STATES\\s*CODE",
   re.IGNORECASE | re.MULTILINE)

## Matches the following formats: 42 USC 1526 42 U.S.C. 1526 42 U.S.
## Code 1526 42 US Code 1526. All previous formats plus the following appendix
## and details 42 USC app. 1526 42 USC appendix 1526 42 USC app. 1526, 1551,
## 1553, 1555, and 1561


usCodeSimple = re.compile(
   "(?P<usc1_p1>[0-9]+)\\s*" + uscT + "(?P<usc1_appendix>" + postAUscT + ")?\\s*(?:SECTIONS?|SEC(TS?)?\\.?)?\\s*(?P<usc1_p2>[0-9]+)",
   re.IGNORECASE | re.MULTILINE)

usCodeShortA2P = re.compile(
   "(?P<usc1_p1>[0-9]+)\\s*" + uscT + "(?P<usc1_appendix>" + postAUscT + ")?\\s*(?:((?:(?:and )?(?P<usc1_p2>\\d+[a-z]*)(?:,\\s*)?)+(?:-[\\w]+)?)((?:\\([\\w]+\\))*\\s*(?:note|et seq\\.)?))",
   re.IGNORECASE | re.MULTILINE)
usCodeLarge2P = re.compile(
   "CHAPTER\\s*(\\d+[a-z]*)(?: \\([^\\)]*\\)) of title (\\d+),\\s*UNITED\\s*STATES\\s*CODE",
   re.IGNORECASE | re.MULTILINE)
usCodeMultiLargeSectionsBP = re.compile(
    "sections?\\s+(.{1,100}?)\\s+of\\s+title\\s+(\\d+)(?:,|\\sof\\s+the)?\\s+united\\s+states\\s+code",
   re.IGNORECASE | re.DOTALL)
usCodeMultiShortSectionsP = re.compile(
   "([0-9]+) [\\s*](./../../%5C%5Cs*)" + uscT + "(?:sections?|sec\\.?)?\\s*" + "((?:" +  singleSectionNoCaptureRegex + "(?!\\s+"  + uscT + ")" + "|and|through|,|\\s)+)",
   re.IGNORECASE | re.MULTILINE)
usCodeMultiShortChaptersP = re.compile(
   "([0-9]+)\\s*" + uscT + "(?:chapters?|ch\\.?)\\s*" + "((?:" + singleChapterNoCaptureRegex + "(?!\\s+"  + uscT + ")" + "|and|through|,|\\s)+)",
   re.IGNORECASE | re.MULTILINE)

statuteAtLargeP = re.compile(
   r"(?P<stat_p1>[0-9]+)\s*STAT\.?\s*(?:L\.)?\s*((?P<stat_p2>[0-9]+)[a-z]*(?:-[0-9]+)?(?: et seq\.)?)",
   re.IGNORECASE | re.MULTILINE)

cfrContentPNew = re.compile(
   "(?P<cfr_p1>[1-50])\\s*CFR\\s*(Secs?\\.?|sections?)*\\s*" +
   "([\\d]+|\\d+|[ILMVX]+),?\\s*" +
   "((?:(?:et (seq|al)\\.)|" +
   "(?:\\s*(and|through|or|,)\\s+)|" +
   "(?:(\\d+,?\\s)+)|" +
   "(?:\\-?\\d+(?:\\.\\d+)?(?:\\([0-9a-z]+\\))*)|" +
   "(?:\\.[0-9a-z]+(?:\\([0-9a-z]+\\))*))+)?",
   re.IGNORECASE | re.MULTILINE)

## END ===

## BEGIN: Our own parser regexes

usReporterP = re.compile(
   r"(?P<usr_p1>[0-9]+)\s*(?:US|U\.S\.)\s*(?P<usr_p2>\d+)",
   re.IGNORECASE | re.MULTILINE)

combinedRe = re.compile(
     r"((?P<usReporter>" + usReporterP.pattern + r"))" +
    r"|((?P<cfr>" + cfrContentPNew.pattern + r"))" +
    r"|((?P<statuteAtLarge>" + statuteAtLargeP.pattern + r"))" +
    r"|((?P<publicLaw>" + publicLawContentP.pattern + r"))" +
    r"|((?P<usCode1>" + usCodeSimple.pattern + r"))" +
    "",
    re.IGNORECASE | re.MULTILINE)

## END ===

## CONSTANTS

_out_header_markdown = Template(u"""---
title: $fancytitle
---

# $fancytitle

* Use of this file is subject to the NOTICE at https://github.com/publicdocs/notice/blob/master/NOTICE
* See the [Document Metadata](../../../index.md) for more information.
  This file is generated from historical government data; content and/or formatting may be inaccurate and out-of-date and should not be used for official purposes.

----------
----------

$linkshtml

----------

$innercontent

----------

$linkshtml

----------
----------

$linksetmd

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

    inc = 0
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
            print u"Processing: " + casename
            comps = casename.split(u' ')
            casevol = comps[-3]
            if casevol.startswith(u'U'):
                casevol = comps[-4]
            if casevol.endswith(u','):
                casevol = casevol[:-1]
            while casevol.endswith(u'.'):
                casevol = casevol[:-1]
            casenum = comps[-1]
            if casenum.endswith('A'):
                casenum = comps[-2]
            while casenum.endswith(u'.'):
                casenum = casevol[:-1]

            if casename == u"TAYLOR V. KENTUCKY 355 U.S.394":
                casevol = 355
                casenum = 394
            if u"BALTIMORE RADIO SHOW, INC." in casename:
                casevol = 338
                casenum = 912
            if casename == u"SACHER V. UNITED STATES 343 U.S.1":
                casevol = 343
                casenum = 1
            casename = casename.strip()

            try:
                casevol = unicode(int(casevol))
            except:
                print "Cannot parse vol: " + casevol


            try:
                casenum = unicode(int(casenum))
            except:
                print "Cannot parse num: " + casenum

            links = []

            uslmid = u'/us/courts/scotus/usReporter/' + casevol + u'/' + casenum


            if not os.path.exists(wdir + u'/' + casevol):
                os.makedirs(wdir + u'/' + casevol)
            outlines2 = []
            for oline in outlines:
                rline = u''
                lastend = 0

                # Hello 3 Stat. 4 Goodbye. 5 U.S.C. 395 kjksdjf
                #       [       ]
                #                          [          ]
                for m in combinedRe.finditer(oline):
                    # print repr(m.groupdict())
                    rline = rline + md_escape(oline[lastend:m.start()])
                    rid = None
                    if m.group('usReporter'):
                        rid = u'/us/courts/scotus/usReporter/' + m.group('usr_p1') + u'/' + m.group('usr_p2')
                    elif m.group('statuteAtLarge'):
                        rid = u'/us/stat/' + m.group('stat_p1') + u'/' + m.group('stat_p2')
                    elif m.group('publicLaw'):
                        rid = u'/us/pl/' + m.group('pl_p1') + u'/' + m.group('pl_p2')
                    elif m.group('cfr'):
                        rid = u'/us/cfr/' + m.group('cfr_p1')
                    elif m.group('usCode1'):
                        rid = u'/us/usc/t' + m.group('usc1_p1')
                        if m.group('usc1_appendix'):
                            rid = rid + u'a'
                        if m.group('usc1_p2'):
                            rid = rid + u'/s' + m.group('usc1_p2')
                    links.append(rid)
                    rline = rline + u"[" + md_escape(oline[m.start():m.end()]) + u"][" + md_escape(rid) + "]"
                    lastend = m.end()
                rline = rline + md_escape(oline[lastend:])
                outlines2.append(rline)

            linksetmd = u''
            for l in links:
                # refcontent md-escaped on construction
                hh = unicode(l)
                rps = u''
                ns = u'uslm'
                if rid.startswith(u'/us/cfr/') or rid.startswith(u'/us/courts/'):
                    ns = ns + u'-x'
                rurl = md_escape(u'https://publicdocs.github.io/go/links?ns=' + ns + u'&' + rps + urllib.urlencode({u'ref' : hh.encode('utf-8')}))
                linksetmd = linksetmd + u'[' + md_escape(l) + u']: ' + rurl + u'\n'

            linkhtml = u''
            rurl = md_escape(u'https://publicdocs.github.io/go/links?ns=uslm-x&' + urllib.urlencode({u'ref' : unicode(uslmid).encode('utf-8')}))
            linkhtml = linkhtml + u'[Other Versions of this Document](' + rurl + u')'

            innercontent = u'\n\n'.join(outlines2)
            of = wdir + u'/' + casevol + u'/' + file_safe_uslm_id(casename[:64]) + u'.md'
            fc = _out_header_markdown.substitute(
                    docmd = '',
                    innercontent = innercontent,
                    fancytitle = md_escape(casename),
                    linkshtml = linkhtml,
                    linksetmd = linksetmd,
            )
            f = open(of, 'w')
            f.write(fc.encode('utf8'))
            f.close()
            inc = inc + 1
            readylines = []
        else:
            readylines.append(l)

    print 'Finished ' + str(inc) + ' cases.'

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
