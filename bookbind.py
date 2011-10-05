#!/usr/bin/env python

# steps:
# - take a directory name to "bind" on the command line
# - read the manifest.yaml file from that directory
# - create a new epub directory
# - copy static files / make directory structure
# - create manifest and TOC files based on the yaml
# - convert the individual chapters based on the templates/css specified
#   - must know whether an HTML file is full or partial...
#   - ...and run "full" files through HTML Tidy

import sys
import os
import zipfile

import yaml
from markdown import markdown
from smartypants import smartyPants
from jinja2 import Environment, FileSystemLoader, exceptions as JE


def manifest_required(fn):
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
    
    def __init__(self, source_dir=None):
        try:
            config_file = open('~/.bookbindrc')
            self.config = yaml.load(config_file.read())
            config_file.close()
        except:
            print "(No valid config file, using defaults)"
        self.source_dir = source_dir


    def load_manifest(self):
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
        except IOError as e:
            raise BinderError(BinderError.NO_MANIFEST,
                'Error reading manifest.yaml file.')


    @manifest_required
    def generate_opf(self):
        return "Foobar"


    @manifest_required
    def generate_toc(self): 
        return "Foobar"


    def make_book(self):
        """Main entry."""
        epub = zipfile.ZipFile(self.source_dir + '.epub', 'w',
                zipfile.ZIP_DEFLATED)
        
        epub.writestr('mimetype', 'application/epub+zip', zipfile.ZIP_STORED)
        epub.write(self.config['static'] + '/container.xml',
                'META-INF/container.xml')
        epub.writestr('OEBPS/content.opf', self.generate_opf())
        epub.writestr('OEBPS/toc.ncx', self.generate_toc())
        
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
        binder = Binder(source_dir)
        binder.load_manifest()
        binder.make_book()
    except BinderError as e:
        print e
        sys.exit(1)
