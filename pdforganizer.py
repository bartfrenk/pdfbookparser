from pdfminer.pdfparser import PDFParser, PDFDocument, PDFNoOutlines
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox, LTTextLine, LTFigure, LTImage

# from denis.papathanasiou.org/tag/pdfminer

def with_pdf(pdf_doc, pdf_pwd, fn, *args):
    """Apply function to extracted pdf document."""
    result = None
    try:
        # open the pdf file
        fp = open(pdf_doc, 'rb')
        # create a parser object associated with the file object
        parser = PDFParser(fp)
        # create a PDFDocument object that stores the document structure
        doc = PDFDocument()
        # connect the parser and document objects
        parser.set_document(doc)
        doc.set_parser(parser)
        # supply the password for initialization
        doc.initialize(pdf_pwd)

        if doc.is_extractable:
            # apply the function and return the result
            result = fn(doc, *args)

        # close the pdf file
        fp.close()
    except IOError:
        # the file does not exist or similar problem
        pass
    return result

def _parse_toc(doc):
    """With an open PDFDocument object, get the table of contents data."""
    toc = []
    try:
        outlines = doc.get_outlines()
        for (level, title, dest, a, se) in outlines:
            toc.append((level, title))
    except PDFNoOutlines:
        pass
    return toc

def _parse_pages(doc, page_numbers, fn):
    """With an open PDFDocument, get the pages, parse each one, and return the entire text."""
    rsrcmgr = PDFResourceManager()
    laparams = LAParams()
    device = PDFPageAggregator(rsrcmgr, laparams = laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    text_content = []
    for i, page in enumerate(doc.get_pages()):
        if page_numbers == True or (i + 1) in page_numbers:
            interpreter.process_page(page)
            # receive the LTPage object for this page
            layout = device.get_result()
            # layout is an LTPage object which may contain child objects like LTTextBox, etc...
            text_content.append(fn(layout, (i+1)))

    return text_content


def parse_lt_objs(lt_objs, page_number, images_folder = '/tmp'):
    """Iterate through the list of LT* objects and capture the text or image data contained in each."""
    text_content = []

    for lt_obj in lt_objs:

        if isinstance(lt_obj, LTTextBox) or isinstance(lt_obj, LTTextLine):
            # text
            pgs = lt_obj.paragraphs(indent_treshold = 4)
            if len(pgs) > 1:
                text_content += parse_lt_objs(pgs, page_number, images_folder, text_content)
            else:
                text_content.append(lt_obj.get_text())

        elif isinstance(lt_obj, LTImage):
            # an image, so save it to the designated folder, and note it's place in the text
            saved_file = save_image(lt_obj, page_number, images_folder)
            if saved_file:
                # use html style <img /> tag to mark the position of the image within the text
                text_content.append('<img src="'+os.path.join(images_folder, saved_file)+'" />')
            else:
                print("Error saving image on page", page_number, lt_obj.__repr__, file = sys.stderr)

        elif isinstance(lt_obj, LTFigure):
            # LTFigure objects are containers for other LT* objects, so recurse through the children
            text_content.append(parse_lt_objs(lt_obj, page_number, images_folder))

        else:
            text_content.append(lt_obj)

    return text_content


def keep_lt_objs(lt_objs, *args):
    return lt_objs

def get_pages(pdf_doc, page_numbers, pdf_pwd = '', fn = parse_lt_objs):
    """Process each of the pages in this pdf file and print the entire text to stdout."""
    return with_pdf(pdf_doc, pdf_pwd, _parse_pages, page_numbers, fn)
