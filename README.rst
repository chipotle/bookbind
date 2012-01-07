Bookbind
========

Bookbind is a Python utility for generating EPUB files. It takes a
directory name as its sole command-line argument and creates an EPUB
file of the same name, with an ``.epub`` extension, in the working
directory. It can natively process Markdown and plain text input files
(as well as XHTML) and can be configured to call external processors for
other input types.

Bookbind expects the directory to be of the following structure:

::

    foo/
        manifest.yaml
        chapter1.md
        chapter2.md
        title-page.xhtml
        styles/
            default.css
        images/
            cover.jpg
            other-image.jpg

The ``manifest.yaml`` file describes the book's metadata and chapter
orders. Consult the sample file for the format and requirements.
 Bookbind's generated files *should* pass ePubChecker with no warnings
or errors. Keep in mind that if you include XHTML files, Bookbind will
add them to your book as-is, so watch for warnings that they might
generate.

In progress
-----------

While Bookbind can be used as-is already, it's missing some
functionality, not all features have been tested, and there's a lot of
rough edges.

The extremely high-level road map:

-  v0.5: Feature complete
-  v0.8: Test suites
-  v1.0: Full documentation and a good default style or two
-  Future:

   -  EPUB 3.0 support
   -  KindleGen support
   -  GUI


