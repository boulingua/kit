# Build the example worksheet with XeLaTeX (needed for fontspec).
TEX ?= xelatex
example: worksheet-template.tex boulingua-sheet.sty
	$(TEX) -interaction=nonstopmode worksheet-template.tex
	$(TEX) -interaction=nonstopmode worksheet-template.tex
clean:
	rm -f *.aux *.log *.out
.PHONY: example clean
