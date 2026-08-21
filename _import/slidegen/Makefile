# Build the example deck with XeLaTeX (needed for fontspec).
TEX ?= xelatex
example: slides-template.tex beamerthemeboulingua.sty
	$(TEX) -interaction=nonstopmode slides-template.tex
	$(TEX) -interaction=nonstopmode slides-template.tex
clean:
	rm -f *.aux *.log *.nav *.snm *.toc *.out *.vrb
.PHONY: example clean
