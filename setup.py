from distutils.core import setup

setup(
    name='Bookbind',
    version='0.4.0',
    author='Watts Martin',
    author_email='layotl@gmail.com',
    packages=['bookbind'],
    scripts=['bin/bookbind.py'],
    url='https://github.com/chipotle/bookbind',
    license='LICENSE.txt',
    description='A command-line EPUB 2.0 creation utility',
    install_requires=[
        'PyYAML',
        'Markdown',
        'smartypants',
        'Jinja2'
    ],
    data_files = [
        ('/usr/local/lib/bookbind/static', ['lib/static/container.xml']),
        ('/usr/local/lib/bookbind/styles', ['lib/styles/default.css']),
        ('/usr/local/lib/bookbind/templates', [
            'lib/templates/chapter.xhtml',
            'lib/templates/content.opf',
            'lib/templates/cover.xhtml',
            'lib/templates/toc.ncx'
        ])
    ]
)
