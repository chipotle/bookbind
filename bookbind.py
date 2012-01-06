#!/usr/bin/env python
import sys
import os
import zipfile
import uuid
import subprocess
from datetime import datetime

import yaml
from markdown import markdown
from smartypants import smartyPants
from jinja2 import Environment, FileSystemLoader, exceptions as JE


def manifest_required(fn):
    """Decorator for functions that require the manifest to be set."""
    def _wrapper(self, *args, **kwargs):
        if self.manifest is None:
            raise BinderError(BinderError.NO_MANIFEST_SET, 'No manifest set')
        return fn(self, *args, **kwargs)
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
    
    DATE_FORMATS = [ '%B %Y', '%b %Y', '%B, %Y', '%b, %Y', '%Y-%b', '%Y-%m' ]
    
    def __init__(self, source_dir=None, config=False):
        self.source_dir = source_dir
        if config:
            self.load_config(config, silent=True)
            self.env = Environment(loader=FileSystemLoader(
                    self.config['templates']))


    def load_config(self, config_filename, silent=False):
        try:
            config_file = open(config_filename)
            self.config = yaml.load(config_file.read())
            config_file.close()
        except Exception as e:
            if silent is False:
                raise e
            else:
                sys.exc_clear()


    def load_manifest(self):
        """Load the manifest.yaml file from the source directory."""
        if self.source_dir is None:
            raise BinderError(BinderError.NO_SOURCE_SET,
                'You must set a source directory.')
        if os.path.exists(self.source_dir) is False:
            raise BinderError(BinderError.NO_FILE,
                'File "{}" not found.'.format(source_dir))
        if os.path.isdir(self.source_dir) is False:
            raise BinderError(BinderError.NOT_A_DIR,
                '"{}" must be a directory.'.format(source_dir))
        
        try:
            manifest_file = open(self.source_dir + '/manifest.yaml')
            self.manifest = yaml.load(manifest_file.read())
            manifest_file.close()
        except IOError:
            raise BinderError(BinderError.NO_MANIFEST,
                'Error reading manifest.yaml file.')


    def templatize(self, template, context):
        tpl = self.env.get_template(template)
        output = tpl.render(context)
        return output.encode('utf_8')


    @manifest_required
    def generate_opf(self):
        return self.templatize('content.opf', {
            'metadata': self.generate_metadata(),
            'manifest': self.generate_manifest_items(),
            'spine': self.generate_spine_items()
        })

    @manifest_required
    def generate_metadata(self):
        """Produce Dublin Core metadata elements from the manifest."""
        metadata = self.manifest['metadata']
        items = []
        flip = lambda x: ((x + ',').split(',')[1].rstrip() + ' ' +
                         (x + ',').split(',')[0].lstrip()).strip()
        if not metadata.has_key('uuid') and not metadata.has_key('isbn'):
            metadata['uuid'] = uuid.uuid4().urn
        if not metadata.has_key('language'):
            metadata['language'] = 'en'
        for elem, value in metadata.items():
            attr = []
            if elem == 'author':
                self.config['author'] = value
                elem = 'creator'
                attr.append('opf:file-as="' + value + '"')
                attr.append('opf:role="aut"')
                value = flip(value)
            elif elem == 'editor':
                elem = 'contributor'
                attr.append('opf:file-as="' + value + '"')
                attr.append('opf:role="edt"')
                value = flip(value)
            elif elem == 'publisher-person':
                elem = 'contributor'
                attr.append('opf:file-as="' + value + '"')
                attr.append('opf:role="pbl"')
                value = flip(value)
            elif elem == 'designer':
                elem = 'contributor'
                attr.append('opf:file-as="' + value + '"')
                attr.append('opf:role="bkd"')
                value = flip(value)
            elif elem == 'title':
                self.config['title'] = value
            elif elem == 'uuid':
                elem = 'identifier'
                attr.append('id="bookid"')
                attr.append('opf:scheme="UUID"')
                self.config['uid'] = value
            elif elem == 'isbn':
                elem = 'identifier'
                attr.append('id="bookid"')
                attr.append('opf:scheme="ISBN"')
                if value.startswith('urn:') is False:
                    value = 'urn:isbn:' + value
                value = value.translate(None, '- ')
                self.config['uid'] = value
            elif elem == 'date':
                for format in self.DATE_FORMATS:
                    new_val = None
                    try:
                        dt = datetime.strptime(value, format)
                        new_val = dt.strftime('%Y-%m')
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
        return items
    
    
    @manifest_required
    def generate_manifest_items(self):
        """Generate items for the OPF manifest element."""
        items = [
            '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
        ]
        for chapter in self.manifest['book']:
            id = self.make_id(chapter['file'])
            items.append('<item id="' + id + '" href="' + id +
                '.xhtml" media-type="application/xhtml+xml"/>')
        if self.manifest.has_key('assets'):
            for asset in self.manifest['assets']:
                for asset_item in asset.items():
                    asset_kind = asset_item[0]
                    asset_list = asset_item[1]
                    for i in asset_list:
                        name, file_ext = os.path.splitext(i)
                        mime_type = self.mime_map.get(file_ext,
                            'application/octet-stream')
                        id = (asset_kind + '_' + name).lower().strip()
                        items.append('<item id="' + id + '" href="' + asset_kind +
                            '/' + i + '" media-type="' + mime_type + '"/>')
        return items
    
    
    def make_id(self, x):
        filename, file_ext = os.path.splitext(x)
        return filename.lower().strip()

    
    @manifest_required
    def generate_spine_items(self):
        items = []
        for chapter in self.manifest['book']:
            id = self.make_id(chapter['file'])
            items.append('<itemref idref="' + id + '"/>')
        return items
    

    @manifest_required
    def generate_toc(self): 
        return self.templatize('toc.ncx', {
            'title': self.config['title'],
            'author': self.config['author'],
            'uid': self.config['uid'],
            'navmap': self.generate_navmap()
        })
    
    
    @manifest_required
    def generate_navmap(self):
        items = []
        for chapter in self.manifest['book']:
            if chapter.has_key('title') and (not chapter.has_key('linear') or chapter['linear'] != False):
                id = self.make_id(chapter['file'])
                items.append({
                    'file': id + '.xhtml',
                    'title': chapter['title'],
                    'id': id
                })
        return items
    
    
    @manifest_required
    def generate_chapter(self, chapter):
        html = False
        filename, file_ext = os.path.splitext(chapter['file'])
        file_ext = file_ext.lower()
        if self.manifest.has_key('stylesheet'):
            stylesheet = self.manifest['stylesheet']
        else:
            stylesheet = 'styles/default.css'
        if self.config.has_key('processors'):
            processors = self.config['processors']
        else:
            processors = {}
        if self.manifest.has_key('processors'):
            processors.append(self.manifest['processors'])
            content = 'fix this'
        if processors.has_key(file_ext):
            command = processors[file_ext].format(chapter['file'])
            html = subprocess.check_output(command.split())
            # just return the HTML if it has a doctype, perhaps? But CSS?
        elif file_ext == '.md' or file_ext == '.txt' or file_ext == '.markdown':
            file_obj = open(self.source_dir + '/' + chapter['file'])
            text = file_obj.read()
            html = smartyPants(markdown(text))
        elif file_ext == '.xhtml':
            file_obj = open(self.source_dir + '/' + chapter['file'])
            return file_obj.read()
        if html is False:
            raise BinderError(BinderError.WEIRD_FILE,
                'Unknown file type: ' + chapter['file'])
        if self.manifest.has_key('stylesheet'):
            stylesheet = self.manifest['stylesheet']
        else:
            stylesheet = 'styles/default.css'
        return self.templatize('chapter.xhtml', {
            'content': html,
            'stylesheet': stylesheet,
            'title': chapter.get('title')
        })

            

# steps:
# - take a directory name to "bind" on the command line
# - read the manifest.yaml file from that directory
# - create a new epub directory
# - copy static files / make directory structure
# - create manifest and TOC files based on the yaml
# - convert the individual chapters based on the templates/css specified
#   - must know whether an HTML file is full or partial...
#   - ...and run "full" files through HTML Tidy

    def make_book(self, outfile=None):
        """Create a complete ePub. This requires the Binder object's manifest
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
            id = self.make_id(chapter['file'])
            epub.writestr('OEBPS/' + id + '.xhtml',
                self.generate_chapter(chapter))
        if self.manifest.has_key('assets'):
            for asset in self.manifest['assets']:
                for asset_item in asset.items():
                    asset_kind = asset_item[0]
                    asset_list = asset_item[1]
                    for i in asset_list:
                        name = asset_kind + '/' + i
                        file_obj = open(self.source_dir + '/' + name)
                        epub.writestr('OEBPS/' + name, file_obj.read())
        epub.close()


def print_help():
    print "BookBinder 0.1\n"
    print "Usage: {} directory\n".format(sys.argv[0])
    print "Create an ePub file from a directory of contents and a YAML manifest file."
    print "Consult the documentation for specifics."


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print_help()
        sys.exit(0)
    
    source_dir = sys.argv[1]
    try:
        binder = Binder(source_dir, '~/.bookbindrc')
        binder.load_manifest()
        binder.make_book()
    except BinderError as e:
        print e
        sys.exit(1)
