//
// Copyright (c) 2016 the authors of the https://github.com/publicdocs project.
// Use of this file is subject to the NOTICE file in the root of the repository.
//

// This works inside a Chrome console window on a slips page like:
// https://www.supremecourt.gov/opinions/slipopinion/10
// and copies the resulting JSON to your clipboard.

results = $('table').filter(function(i) { return $(this).find(':contains("Pt.")').length; });
rows = results.children('tbody').children('tr');
jsons = []
vals = rows.each(function(a) {
  d = {
    'r_seq':$(this).children(':nth-child(1)').text(),
    'date_decided':$(this).children(':nth-child(2)').text(),
    'docket':$(this).children(':nth-child(3)').text(),
    'caption':$(this).children(':nth-child(4)').text(),
    'caption_tooltip':$(this).children(':nth-child(4)').find('a').attr('title'),
    'link':$(this).find('a').first().attr('href'), // download the last revised url, but the later urls are of the correction diffs
    'justice':$(this).children(':nth-last-child(2)').text(),
    'pt':$(this).children(':nth-last-child(1)').text()
  };
jsons.push(d);
});
cop = JSON.stringify(jsons, null, 2);
copy(cop + '\n');
