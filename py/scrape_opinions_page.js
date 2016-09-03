//
// Copyright (c) 2016 the authors of the https://github.com/publicdocs project.
// Use of this file is subject to the NOTICE file in the root of the repository.
//

// This works inside a Chrome console window on an opinions index page like:
// https://www.supremecourt.gov/opinions/03pdf/
// and copies the resulting JSON to your clipboard.

rows = $('center').first().children('a');
jsons = []
vals = rows.each(function(a) {
  d = {
    'caption':$(this).text(),
    'link':window.location + $(this).attr('href'),
    'docket':$(this).attr('href').slice(0,-4)
  };
jsons.push(d);
});
cop = JSON.stringify(jsons, null, 2);
copy(cop + '\n');
