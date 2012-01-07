# Bookbind

Bookbind is a Python utility for generating EPUB files. It takes a directory name as its sole command-line argument and creates an EPUB file of the same name, with an `.epub` extension, in the working directory. It can natively process Markdown and plain text input files (as well as XHTML) and can be configured to call external processors for other input types.

Bookbind expects the directory to be of the following structure:

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

The `manifest.yaml` file describes the book's metadata and chapter orders. Consult the sample file for the format and requirements.\

Bookbind's generated files _should_ pass ePubChecker with no warnings or errors. Keep in mind that if you include XHTML files, Bookbind will add them to your book as-is, so watch for warnings that they might generate.

## Future Enhancements

Bookbind is currently considered "pre-release" by its author, but it's already capable of generating complete books that pass `epubcheck` 1.0.5's compliance text. The work to do before 1.0 must include:

* Creation of a test suite
* Ensuring Pandoc and MultiMarkdown can be used as external processors
* Verification that a `distuils`-created tarball really installs correctly
* Full documentation file

At that point, Bookbind will be submitted to PyPI.

Other enhancements under consideration:

* Creating new default styles for the distribution
* EPUB 3.0 support
* Optional creation of a hyperlink TOC page for lazy people like me
* Optional MOBI creation if `kindlegen` is installed
