"""
Script that generates a formatted table of supported languages
for the CompileBot wiki.
"""
import yaml
import ideone

SETTINGS_FILE = 'compilebot/config.yml'
with open(SETTINGS_FILE, 'r') as f:
    SETTINGS = yaml.load(f)

i = ideone.Ideone(SETTINGS['ideone_user'], SETTINGS['ideone_pass'])
languages = i.languages()
simple_langs = dict((k,v.split('(')[0].strip())
                    for (k,v) in languages.items())
lang_shortcuts = SETTINGS['lang_aliases']

table = "Language Name | Short Names \n---------|----------\n"
rows = []
count = 0
for num, lang in languages.items():
    shortcuts = ''
    simple_name = simple_langs[num]
    for shortcut, simple in lang_shortcuts.items():
        if simple.lower() == simple_name.lower():
            shortcuts += ', {}'.format(shortcut)
    rows.append("{}|{}\n".format(lang, simple_name + shortcuts))
    count += 1
rows.sort(key=lambda s: s.lower())
table += ''.join(rows)
print(table)
print("Total Languages {}".format(count))
