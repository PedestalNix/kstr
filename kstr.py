import pathlib
import re
import shelve
import textwrap
from collections import namedtuple

import click

TextLine = namedtuple('TextLine', ['key', 'text', 'eol'])


@click.group()
def cli():
    pass


@cli.command()
@click.argument('paths',
                type=click.Path(exists=True,
                                dir_okay=False,
                                resolve_path=True,
                                path_type=pathlib.Path),
                nargs=-1)
@click.option('--outpath',
              type=click.Path(dir_okay=False,
                              resolve_path=True,
                              path_type=pathlib.Path),
              default=pathlib.Path('./project/source/trans.txt'))
@click.option('--workpath',
              type=click.Path(file_okay=False,
                              resolve_path=True,
                              path_type=pathlib.Path),
              default=pathlib.Path('./working/'))
def extract(paths, outpath, workpath):
    # paths = inpath.glob('*.ks')
    trans = []

    workpath.mkdir(parents=True, exist_ok=True)
    outpath.parent.mkdir(parents=True, exist_ok=True)

    command_starts = {'[', '*', ';'}
    MACROS = r'(?P<text>.*?)(?P<eol>(?:\[[^\]]+\])+)$'

    for path in paths:
        newlines = []
        text = None
        with open(path, 'r', encoding='shift_jis') as f:
            try:
                text = f.read()
            except Exception:
                print("failed to read", path.name)
        if text is None:
            with open(path, 'r', encoding='utf_8') as f:
                try:
                    text = f.read()
                except Exception:
                    print("failed to read", path.name)
                    raise
        group = ''
        groupkey = None
        for i, line in enumerate(text.splitlines()):
            if line == '' or any(line.strip().startswith(s) for s in command_starts):
                if group:
                    newlines.append(groupkey)
                    trans.append(TextLine(groupkey, group, ''))
                    group = ''
                    groupkey = None
                newlines.append(line)
            else:
                key = '<<<TRANS:{}-{}>>>'.format(path.name, i)
                if (m := re.match(MACROS, line.strip())):
                    eol = m.group('eol')
                    text = m.group('text')
                    if eol == '[r]':
                        if not groupkey:
                            groupkey = key
                        group += text
                    else:
                        if group:
                            group += text
                            newlines.append(groupkey)
                            trans.append(TextLine(groupkey, group, eol))
                            group = ''
                            groupkey = None
                        else:
                            newlines.append(key)
                            trans.append(TextLine(key, text, eol))
                else:
                    # This is one logical line, no pause, continued over multiple lines on screen.
                    if not groupkey:
                        groupkey = key
                    group += line.strip()

        with open(workpath / path.name, 'w', encoding='shift_jis') as f:
            f.write('\n'.join(newlines))

    with open(outpath, 'w', encoding='utf_8') as f:
        for t in trans:
            f.write(t.text + '\n')

    with shelve.open(str(workpath / 'trans.shelf')) as shelf:
        shelf['lines'] = trans


@cli.command()
@click.argument('inpath',
                type=click.Path(exists=True,
                                dir_okay=False,
                                resolve_path=True,
                                path_type=pathlib.Path),
                default=pathlib.Path('./project/target/trans.txt'))
@click.option('--outpath',
                type=click.Path(file_okay=False,
                                resolve_path=True,
                                path_type=pathlib.Path),
                default=pathlib.Path('./patch/'))
@click.option('--workpath',
                type=click.Path(file_okay=False,
                                resolve_path=True,
                                path_type=pathlib.Path),
                default=pathlib.Path('./working/'))
def insert(inpath, outpath, workpath):
    paths = workpath.glob('*.ks')
    with shelve.open(str(workpath / 'trans.shelf')) as shelf:
        intrans = {t.key: t for t in shelf['lines']}

    with open(inpath, 'r', encoding='utf_8') as vs:
        tlines = dict(zip(list(intrans.keys()), list(vs)))

    trans = {}
    for k, v in tlines.items():
        try:
            trans[k] = TextLine(k, v, intrans[k.strip()].eol)
        except Exception:
            print("keys: {!r}", list(intrans.keys())[:5])
            raise

    for path in paths:
        newlines = []
        text = None
        with open(path, 'r', encoding='shift_jis') as f:
            try:
                text = f.read()
            except Exception:
                print("failed to read", path.name)
        if text is None:
            with open(path, 'r', encoding='utf_8') as f:
                try:
                    text = f.read()
                except Exception:
                    print("failed to read", path.name)
                    raise
        for line in text.splitlines():
            if (m := re.match(r'<<<TRANS:{}-\d+>>>'.format(path.name), line)):
                text = '[r]\n'.join(textwrap.wrap(
                    trans[m.group(0)].text.strip(),
                    width=40))
                newlines.append(text + trans[m.group(0)].eol)
            else:
                newlines.append(line)

        with open(outpath / path.name, 'w', encoding='shift_jis', errors='replace') as f:
            f.write('\n'.join(newlines))
