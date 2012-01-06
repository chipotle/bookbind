#!/usr/bin/env python
import sys
from bookbind import bookbind

def print_help():
    print "BookBinder 0.4\n"
    print "Usage: {} directory\n".format(sys.argv[0])
    print "Create an ePub file from a directory of contents and a YAML manifest file."
    print "Consult the documentation for specifics."


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print_help()
        sys.exit(0)
    
    source_dir = sys.argv[1]
    try:
        binder = bookbind.Binder(source_dir, '~/.bookbindrc')
        binder.load_manifest()
        binder.make_book()
    except bookbind.BinderError as e:
        print e
        sys.exit(1)
