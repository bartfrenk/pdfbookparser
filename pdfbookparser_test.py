#! /usr/bin/python3

from pdb import set_trace
from pdfbookparser import PreprocessParser, FeatureParser, Frame

parser = FeatureParser(content_frame = Frame(65, 90, 410, 620),
                       text_heights = {'p': 12.9, 'fn_size': 9.5, 'h1': 15.6, 'h2': 13.4},
                       text_height_af = 0.02)

parser.set_pdf('atoj.pdf')
print(parser.params)
result = parser.parse(range(12, 27))
L = [item for sublist in result for item in sublist]
txt = "\n".join(L)
f = open('test.html', 'w')
f.write(txt)
f.close()
