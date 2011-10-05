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

class BinderError(Exception):
    """Exception class. Use constants below for error handling."""
    NO_FILE = 100
    NOT_A_DIR = 101
    NO_MANIFEST = 102
    
    def __init__(self, code, msg):
        self.code = code
        self.msg = msg
    
    def __str__(self):
        return '[Err {}] {}'.format(self.code, self.msg)


def do_mdown(value, smarty=True):
    """Wrapper for markdown for Jinja2 filter."""
    html = markdown(value)
    if smarty:
        html = smartyPants(html)
    return html


def do_smarty(value):
    """Wrapper for smartypants for Jinja2 filter."""
    return smartyPants(value)


def get_config():
    config = {
        'static': '/usr/local/lib/bookbind/static',
        'templates': '/usr/local/lib/bookbind/templates',
        'styles': '/usr/local/lib/bookbind/styles'
    }
    try:
        config_file = open('~/.bookbindrc')
        config = yaml.load(config_file.read())
        config_file.close()
    except:
        print "(No valid config file, using defaults)"
    return config


def generate_opf():
    return """Bacon ipsum dolor sit amet cow occaecat shankle cillum beef biltong. Headcheese tail bacon, sausage consequat elit sunt nostrud voluptate excepteur. Eu turkey minim adipisicing tail, biltong exercitation jowl ut ut short loin in nisi ut. Chicken reprehenderit pig meatball, swine shank tempor id. Flank aliqua beef ribs, ham hock pig eu beef minim short loin. Short ribs dolore fatback bacon, pancetta tenderloin ham hock fugiat excepteur pariatur strip steak biltong ut proident. Consectetur ea pastrami pork belly reprehenderit jerky.

Incididunt in occaecat, fatback officia voluptate ut excepteur headcheese ullamco ground round. Incididunt dolore eiusmod, sint short loin id brisket est pork chop corned beef cupidatat nostrud. Deserunt bresaola aute pork chop. Andouille t-bone do, ex quis pastrami pancetta tongue. Bacon deserunt boudin, tri-tip sunt esse meatball. Bresaola shank non adipisicing jerky. Fatback shoulder deserunt, sunt occaecat quis exercitation meatloaf fugiat.

Headcheese nostrud ut fatback, pastrami ut commodo pork corned beef incididunt irure. Consequat deserunt mollit qui anim incididunt. Ea anim laborum flank. Tempor ex in tongue, qui do strip steak short ribs minim elit chuck sint. Elit boudin drumstick, chicken ball tip aliqua in jerky dolore turkey pariatur ribeye. Jowl corned beef strip steak, sausage bresaola shankle meatball culpa beef ribs drumstick consequat. Esse bacon tail, hamburger aliqua culpa aliquip short ribs laboris sausage.

Consequat jerky boudin sirloin. Tempor do shoulder, ribeye t-bone exercitation qui boudin. Flank meatball bacon, elit tenderloin spare ribs in meatloaf deserunt corned beef id. Deserunt nisi consectetur tenderloin proident shank. Commodo nisi strip steak minim. Cow aute elit, laboris sed hamburger proident dolor veniam. Shankle jowl in bresaola hamburger strip steak.

Mollit ad proident, excepteur in pork belly boudin anim corned beef laborum. Ut exercitation turkey, pork belly venison fugiat mollit jerky. Cillum voluptate in rump ribeye, bacon elit sunt tail aliqua duis qui magna flank. Pastrami laborum fugiat, beef ribs corned beef turkey adipisicing ham aliquip t-bone. Boudin meatloaf est, salami fatback sausage pariatur ribeye exercitation chicken qui pork loin occaecat bresaola. Hamburger jowl meatball do, ut est boudin duis consectetur. Adipisicing qui venison sunt."""


def generate_toc(): 
    return generate_opf()


def make_book(source_dir):
    """Main entry. The parameter must be a directory with the files to bind
    and a YAML manifest.
    
    """
    config = get_config()
    
    if os.path.exists(source_dir) is False:
        raise BinderError(BinderError.NO_FILE,
            'File "{}" not found.'.format(source_dir))
    
    if os.path.isdir(source_dir) is False:
        raise BinderError(BinderError.NOT_A_DIR,
            '"{}" must be a directory.'.format(source_dir))
    
    try:
        manifest_file = open(source_dir + '/manifest.yaml')
        manifest = yaml.load(manifest_file.read())
        manifest_file.close()
    except IOError as e:
        raise BinderError(BinderError.NO_MANIFEST,
            'Error reading manifest.yaml file.')
    
    epub = zipfile.ZipFile(source_dir + '.epub', 'w', zipfile.ZIP_DEFLATED)
    
    epub.writestr('mimetype', 'application/epub+zip', zipfile.ZIP_STORED)
    epub.write(config['static'] + '/container.xml', 'META-INF/container.xml')
    epub.writestr('OEBPS/content.opf', generate_opf())
    epub.writestr('OEBPS/toc.ncx', generate_toc())
    
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
        make_book(sys.argv[1])
    except BinderError as e:
        print e
        sys.exit(1)
