#!/usr/bin/env python
"""Bookbind - EPUB creation library"""
import sys
import os
import zipfile
import uuid
import subprocess
from datetime import datetime

import yaml
from markdown import markdown, MarkdownException
from smartypants import smartyPants
from jinja2 import Environment, FileSystemLoader

__VERSION__ = '0.5.1'


def manifest_required(func):
    """Decorator for functions that require the manifest to be set."""
    def _wrapper(self, *args, **kwargs):
        if self.manifest is None:
            raise BinderError(BinderError.NO_MANIFEST_SET, 'No manifest set')
        return func(self, *args, **kwargs)
    return _wrapper


class BinderError(Exception):
    """Exception class. Use constants below for error handling."""
    NO_FILE = 100
    NOT_A_DIR = 101
    NO_MANIFEST = 102
    NO_SOURCE_SET = 103
    NO_MANIFEST_SET = 104
    WEIRD_FILE = 105
    
    def __init__(self, code, msg):
        self.code = code
        self.msg = msg
    
    def __str__(self):
        return '[Err {}] {}'.format(self.code, self.msg)


def make_id(fullname):
    """Produce a simple ID from a filename. This may also be used to
    create filenames at certain places.
    
    """
    filename, file_ext = os.path.splitext(fullname)
    return filename.lower().strip()


class Binder:
    """Binder class."""

    # Class variables/defaults
    config = {
        'static': '/usr/local/lib/bookbind/static',
        'templates': '/usr/local/lib/bookbind/templates',
        'styles': '/usr/local/lib/bookbind/styles'
    }
    manifest = None
    source_dir = None
    env = None
    images = 'images'
    styles = 'styles'
    other = 'assets'
    mime_map = {
        '.js': 'application/javascript',
        '.mp3': 'audio/mpeg',
        '.ogg': 'audio/ogg',
        '.gif': 'image/gif',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.svg': 'image/svg+xml',
        '.html': 'application/xhtml+xml', # EPUB 2.x spec = XHTML always!
        '.txt': 'text/plain',
        '.xml': 'text/xml',
        '.css': 'text/css',
        '.xhtml': 'application/xhtml+xml',
        '.otf': 'application/x-font-otf',
        '.ttf': 'application/x-font-ttf',
        '.mp4': 'audio/mp4',
        '.m4v': 'video/mpeg4',
        '.qt': 'video/quicktime',
        '.webm': 'video/webm',
    }
    date_formats = [ '%B %Y', '%b %Y', '%B, %Y', '%b, %Y', '%Y-%b', '%Y-%m' ]
    remap_values = {
        'author': ('creator', 'aut'),
        'editor': ('contributor', 'edt'),
        'publisher-person': ('contributor', 'pbl'),
        'designer': ('contributor', 'bkd')
    }
    
    def __init__(self, source_dir=None, config=False):
        self.source_dir = source_dir
        if config:
            self.load_config(config, silent=True)
            self.env = Environment(loader=FileSystemLoader(
                    self.config['templates']))


    def load_config(self, config_filename, silent=False):
        """Load configuration file."""
        try:
            config_file = open(config_filename)
            self.config = yaml.load(config_file.read())
            config_file.close()
        except Exception as err:
            if silent is False:
                raise err
            else:
                sys.exc_clear()


    def load_manifest(self):
        """Load the manifest.yaml file from the source directory."""
        if self.source_dir is None:
            raise BinderError(BinderError.NO_SOURCE_SET,
                'You must set a source directory.')
        if os.path.exists(self.source_dir) is False:
            raise BinderError(BinderError.NO_FILE,
                'File "{}" not found.'.format(self.source_dir))
        if os.path.isdir(self.source_dir) is False:
            raise BinderError(BinderError.NOT_A_DIR,
                '"{}" must be a directory.'.format(self.source_dir))
        
        try:
            manifest_file = open(self.source_dir + '/manifest.yaml')
            self.manifest = yaml.load(manifest_file.read())
            manifest_file.close()
        except IOError:
            raise BinderError(BinderError.NO_MANIFEST,
                'Error reading manifest.yaml file.')


    def templatize(self, template, context):
        """Return a rendered template, given the template (as a string)
        and the context dictionary as parameters.
        
        """
        tpl = self.env.get_template(template)
        output = tpl.render(context)
        return output.encode('utf_8')


    @manifest_required
    def generate_opf(self):
        """Return the complete content.opf file contents."""
        return self.templatize('content.opf', {
            'metadata': self.generate_metadata(),
            'manifest': self.generate_manifest_items(),
            'spine': self.generate_spine_items(),
            'cover': self.manifest.get('cover')
        })

    @manifest_required
    def generate_metadata(self):
        """Produce Dublin Core metadata elements from the manifest."""
        metadata = self.manifest['metadata']
        items = []
        if not metadata.has_key('uuid') and not metadata.has_key('isbn'):
            metadata['uuid'] = uuid.uuid4().urn
        if not metadata.has_key('language'):
            metadata['language'] = 'en'
        for elem, value in metadata.items():
            attr = []
            if elem == 'author' or elem == 'title':
                self.config[elem] = value
            attr, elem, value = self.dublin_remap(attr, elem, value)
            if elem == 'uuid' or elem == 'isbn':
                elem = 'identifier'
                attr.append('id="bookid"')
                attr.append('opf:scheme="' + elem.upper() + '"')
                if elem == 'isbn':
                    value = 'urn:isbn:' + value.translate(None, '- ')
                self.config['uid'] = value
            elif elem == 'date':
                for date_fmt in self.date_formats:
                    new_val = None
                    try:
                        stamp = datetime.strptime(value, date_fmt)
                        new_val = stamp.strftime('%Y-%m')
                        break
                    except ValueError:
                        pass
                if new_val is None:
                    raise ValueError()
                value = new_val
            attrs = ' '.join(attr)
            if attrs != '':
                attrs = ' ' + attrs
            items.append('<dc:' + elem + attrs + '>' + value +
                         '</dc:' + elem + '>')
        if self.manifest.has_key('cover'):
            name, ext = os.path.splitext(self.manifest['cover'])
            img_id = self.images + '_' + name
            items.append('<meta name="cover" content="' + img_id +'"/>')
        return items
    
    
    def dublin_remap(self, attr, elem, value):
        """Remap bookbinder metadata to Dublin Core elements."""
        if self.remap_values.has_key(elem):
            flip = lambda x: ((x + ',').split(',')[1].rstrip() + ' ' +
                             (x + ',').split(',')[0].lstrip()).strip()
            dc_element = self.remap_values[elem]
            elem = dc_element[0]
            attr.append('opf:file-as="' + value + '"')
            attr.append('opf:role="' + dc_element[1] + '"')
            value = flip(value)
        return attr, elem, value

    
    @manifest_required
    def generate_manifest_items(self):
        """Generate items for the OPF manifest element."""
        items = [
            '<item id="ncx" href="toc.ncx" ' +
            'media-type="application/x-dtbncx+xml"/>'
        ]
        if self.manifest.has_key('cover'):
            items.append('<item id="cover" href="cover.xhtml" ' +
                'media-type="application/xhtml+xml"/>')
        for chapter in self.manifest['book']:
            chapter_id = make_id(chapter['file'])
            items.append('<item id="' + chapter_id + '" href="' + chapter_id +
                '.xhtml" media-type="application/xhtml+xml"/>')
        items = self.add_assets(items)
        return items
    
    
    def add_assets(self, items):
        """Add the assets to the manifest item list."""
        stylesheet = self.manifest.get('stylesheet', 'default.css')
        if os.access(self.source_dir + '/' + self.styles + '/' + stylesheet,
        os.R_OK) is False:
            name, ext = os.path.splitext(stylesheet)
            asset_id = (self.styles + '_' + name).lower().strip()
            items.append('<item id="' + asset_id + '" href="' + self.styles +
                '/' + stylesheet + '" media-type="text/css"/>')
        for dir_name in (self.images, self.styles, self.other):
            full_dir = self.source_dir + '/' + dir_name
            if os.access(full_dir, os.R_OK):
                files = os.listdir(full_dir)
                for myfile in files:
                    name, ext = os.path.splitext(myfile)
                    mime_type = self.mime_map.get(ext,
                        'application/octet-stream')
                    file_id = (dir_name + '_' + name).lower().strip()
                    items.append('<item id="' + file_id + '" href="' +
                        dir_name + '/' + myfile + '" media-type="' + mime_type
                        + '"/>')
        return items
    
    
    @manifest_required
    def generate_spine_items(self):
        """Generate the items for the OPF spine element."""
        if self.manifest.has_key('cover'):
            items = ['<itemref idref="cover"/>']
        else:
            items = []
        for chapter in self.manifest['book']:
            chapter_id = make_id(chapter['file'])
            items.append('<itemref idref="' + chapter_id + '"/>')
        return items
    

    @manifest_required
    def generate_toc(self): 
        """Return the contents of the toc.ncx file."""
        return self.templatize('toc.ncx', {
            'title': self.config['title'],
            'author': self.config['author'],
            'uid': self.config['uid'],
            'navmap': self.generate_navmap()
        })
    
    
    @manifest_required
    def generate_navmap(self):
        """Generate the NCX navmap element."""
        items = []
        for chapter in self.manifest['book']:
            if chapter.has_key('title') and (not chapter.has_key('linear')
            or chapter['linear'] != False):
                chapter_id = make_id(chapter['file'])
                items.append({
                    'file': chapter_id + '.xhtml',
                    'title': chapter['title'],
                    'id': chapter_id
                })
        return items
    
    
    @manifest_required
    def generate_chapter(self, chapter):
        """Return a rendered 'chapter' given a chapter element from the
        manifest. This uses the extension of the input file to determine the
        processing (if any) to be done. First external processors defined in
        the configuration file are checked; otherwise, the internal Markdown
        processor is used for .md/.txt files. XHTML files are used as-is.
        
        """
        html = False
        filename, file_ext = os.path.splitext(chapter['file'])
        file_ext = file_ext.lower()
        stylesheet = self.styles + '/' + chapter.get('stylesheet',
            self.manifest.get('stylesheet', 'default.css'))
        processors = self.config.get('processors', {})
        if processors.has_key(file_ext):
            command = processors[file_ext].format(chapter['file'])
            try:
                html = subprocess.check_output(command.split())
            except:
                print "Error running '{}'".format(chapter['file'])
                sys.exit(1)
            # TODO handle partial or full HTML output here
        elif file_ext == '.md' or file_ext == '.txt' or file_ext == '.markdown':
            try:
                file_obj = open(self.source_dir + '/' + chapter['file'])
                text = file_obj.read()
            except IOError as err:
                print err
                sys.exit(1)
            try:
                html = smartyPants(markdown(text))
            except MarkdownException as err:
                print "Error processing {} - {}".format(chapter['file'], err)
                sys.exit(1)
        elif file_ext == '.xhtml':
            file_obj = open(self.source_dir + '/' + chapter['file'])
            return file_obj.read()
        if html is False:
            raise BinderError(BinderError.WEIRD_FILE,
                'Unknown file type: ' + chapter['file'])
        return self.templatize('chapter.xhtml', {
            'content': html,
            'stylesheet': stylesheet,
            'title': chapter.get('title')
        })
    
    
    @manifest_required
    def generate_cover(self):
        """Generate a cover wrapper around the supplied cover image."""
        return self.templatize('cover.xhtml', {
            'image': self.images + '/' + self.manifest['cover'],
            'title': self.config['title']
        })
    

    def make_book(self, outfile=None):
        """Create a complete EPUB. This requires the Binder object's manifest
        property to be set, either by loading a manifest.yaml file with the
        load_manifest() method or by setting it directly. If the outfile
        argument is specified, it is used as the output directory and book
        name (do not include the ".epub" extension, as it will be added);
        otherwise, the epub file will be created with the same name as the
        source directory (i.e., if processing ~watts/greatbook/, the output
        file will be ~watts/greatbook.epub).
        
        """
        if outfile is None:
            outfile = self.source_dir
        epub = zipfile.ZipFile(outfile + '.epub', 'w', zipfile.ZIP_DEFLATED)
        
        epub.writestr('mimetype', 'application/epub+zip', zipfile.ZIP_STORED)
        epub.write(self.config['static'] + '/container.xml',
                'META-INF/container.xml')
        epub.writestr('OEBPS/content.opf', self.generate_opf())
        epub.writestr('OEBPS/toc.ncx', self.generate_toc())
        for chapter in self.manifest['book']:
            chapter_id = make_id(chapter['file'])
            epub.writestr('OEBPS/' + chapter_id + '.xhtml',
                self.generate_chapter(chapter))
        if self.manifest.has_key('cover'):
            epub.writestr('OEBPS/cover.xhtml', self.generate_cover())
        if self.manifest.has_key('stylesheet'):
            sheet = '/' + self.styles + '/' + self.manifest['stylesheet']
            if os.access(self.source_dir + sheet, os.R_OK) is False:
                epub.write(
                    self.config['styles'] + '/' + self.manifest['stylesheet'],
                    'OEBPS/' + sheet
                )
        for asset_dir in (self.images, self.styles, self.other):
            full_dir = self.source_dir + '/' + asset_dir
            if os.access(full_dir, os.R_OK):
                files = os.listdir(full_dir)
                for myfile in files:
                    file_obj = open(full_dir + '/' + myfile)
                    epub.writestr('OEBPS/' + asset_dir + '/' + myfile,
                        file_obj.read())
        epub.close()
