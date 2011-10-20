#!/usr/bin/env python
import sys
import os
import zipfile
import uuid
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


    def load_manifest(self, manifest=None):
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
                elem = 'creator'
                attr.append('opf:file-as="' + value + '"')
                attr.append('role="aut"')
                value = flip(value)
            elif elem == 'editor':
                elem = 'contributor'
                attr.append('opf:file-as="' + value + '"')
                attr.append('role="edt"')
                value = flip(value)
            elif elem == 'publisher-person':
                elem = 'contributor'
                attr.append('opf:file-as="' + value + '"')
                attr.append('role="pbl"')
                value = flip(value)
            elif elem == 'designer':
                elem = 'contributor'
                attr.append('opf:file-as="' + value + '"')
                attr.append('role="bkd"')
                value = flip(value)
            elif elem == 'uuid':
                elem = 'identifier'
                attr.append('id="bookid"')
                attr.append('opf:scheme="UUID"')
            elif elem == 'isbn':
                elem = 'identifier'
                attr.append('id="bookid"')
                attr.append('opf:scheme="ISBN"')
                if value.startswith('urn:') is False:
                    value = 'urn:isbn:' + value
                value = value.translate(None, '- ')
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
        items = [
            '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
        ]
        return items
    
    
    @manifest_required
    def generate_spine_items(self):
        items = [
            '<itemref idref="FooBar"/>'
        ]
        return items
    

    @manifest_required
    def generate_toc(self): 
        return "Foobar"

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
        """Main entry."""
        if outfile is None:
            outfile = self.source_dir
        epub = zipfile.ZipFile(outfile + '.epub', 'w', zipfile.ZIP_DEFLATED)
        
        epub.writestr('mimetype', 'application/epub+zip', zipfile.ZIP_STORED)
        epub.write(self.config['static'] + '/container.xml',
                'META-INF/container.xml')
        epub.writestr('OEBPS/content.opf', self.generate_opf())
        epub.writestr('OEBPS/toc.ncx', self.generate_toc())
        epub.close()
        print self.manifest['book']
    


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
