from pdfminer.pdfparser import PDFParser, PDFDocument, PDFNoOutlines
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox, LTTextLine, LTFigure, LTImage

def html_start(tag):
    return "<" + tag + ">"

def html_end(tag):
    return "</" + tag + ">"

class Frame:

    def __init__(self, x0, y0, x1, y1):
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1

    def contains(self, lt_obj):
        return (self.x0 <= lt_obj.x0 and self.y0 <= lt_obj.y0) and \
               (lt_obj.x1 <= self.x1 and lt_obj.y1 <= self.y1)



class BaseParser:


    def __init__(self, **params):
        self.params['images_folder'] = '/tmp'
        self.set_params(**params)

    def set_params(self, **params):
        self.params.update(params)

    def delete_params(self, *params):
        for key in params:
            del self.params[key]

    def set_pdf(self, pdf_doc, pdf_pwd = ''):
        self._pdf_doc = pdf_doc
        self._pdf_pwd = pdf_pwd

    def parse(self, page_numbers = True, *args):
        result = None
        try:
            # open the pdf file
            fp = open(self._pdf_doc, 'rb')
            # create a parser object associated with the file object
            parser = PDFParser(fp)
            # create a PDFDocument object that stores the document structure
            doc = PDFDocument()
            # connect the parser and document objects
            parser.set_document(doc)
            doc.set_parser(parser)
            # supply the password for initialization
            doc.initialize(self._pdf_pwd)

            if doc.is_extractable:
                # apply the function and return the result
                result = self.parse_doc(doc, page_numbers, *args)

            # close the pdf file
            fp.close()

        except IOError:
            # the file does not exist or similar problem
            pass

        return result


    def parse_doc(self, doc, page_numbers):
        return doc



class PreprocessParser (BaseParser):


    def __init__(self, **params):
        self.params = {'indent_treshold': 4,
                       'content_cls': [LTTextBox, LTTextLine, LTImage, LTFigure]}
        super(PreprocessParser, self).__init__(**params)

    def parse_doc(self, doc, page_numbers):
        rsrcmgr = PDFResourceManager()
        laparams = LAParams()
        device = PDFPageAggregator(rsrcmgr, laparams = laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)

        result = []
        for i, page in enumerate(doc.get_pages()):
            if page_numbers == None or (i + 1) in page_numbers:
                interpreter.process_page(page)
                # receive the LTPage object for this page and prepare it for parsing
                layout = self.preprocess(device.get_result())
                # layout is an LTPage object which may contain child objects like LTTextBox, etc...
                result.append(self.parse_lt_objs(layout, (i+1)))

        return result


    def preprocess(self, lt_objs):
        layout = []

        for lt_obj in lt_objs:
            if self.is_relevant(lt_obj):
                # exclude text outside of a central frame, i.e. page numbers, headers
                if hasattr(lt_obj, 'paragraphs'):
                    # split text into paragraphs
                    layout += lt_obj.paragraphs(indent_treshold = self.params['indent_treshold'])
                else:
                    layout.append(lt_obj)

        return layout

    def is_relevant(self, lt_obj):
        # is the LT object contained in the central frame?
        in_frame = (not 'content_frame' in self.params) or \
                   (self.params['content_frame'].contains(lt_obj))
        # does the LT object contain visual or textual content?
        has_content = not 'content_cls' in self.params or \
                      any(isinstance(lt_obj, cls) for cls in self.params['content_cls'])
        return in_frame and has_content


    def parse_lt_objs(self, lt_objs, page_number):
        return [lt_obj for lt_obj in lt_objs]


class FeatureParser (PreprocessParser):

    def parse_lt_objs(self, lt_objs, page_number):
        text_content = []
        footnote_content = []
        n = len(lt_objs)

        for i, lt_obj in enumerate(lt_objs):

            if isinstance(lt_obj, LTTextBox) or isinstance(lt_obj, LTTextLine):
                # text
                tag = self.get_text_tag(lt_obj, i + 1, n)
                if tag != 'footnote':
                    text = lt_obj.get_text().replace("\n", " ").strip()
                    if text:
                    # text is not just spaces
                        text_content.append(html_start(tag) +
                                            lt_obj.get_text().replace("\n", " ") +
                                            html_end(tag))
                else:
                    # TODO: add unique anchors to the footnotes
                    footnote_content.append(lt_obj.get_text().replace("\n", " "))


            elif isinstance(lt_obj, LTImage):
                # an image, so save it to the designated folder, and note it's place in the text
                saved_file = save_image(lt_obj, page_number, self.params['images_folder'])
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

    def get_text_tag(self, lt_obj, index, lt_obj_count):
        tag = None
        text_size = self.get_text_size(lt_obj.height / len(lt_obj))
        if text_size == 'fn_size':
            tag = 'footnote'
        else:
            tag = text_size
        return tag

    def get_text_size(self, avg_lineheight):
        """Give semantic classification of the object based on its average lineheight."""
        result = 'p'
        # TODO: think of a better name, af stands for approximation factor
        af = self.params.get('text_height_af', 0)
        text_heights = self.params.get('text_heights', {})
        for key, height in text_heights.items():
            if (1 - af) * height <= avg_lineheight and (1 + af) * height >= avg_lineheight:
                result = key
        return result

