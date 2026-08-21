# Build the example deck and worksheet with XeLaTeX (fontspec requires it).
#
# The .sty files resolve fonts/, brand/icons/ and assets/ relative to the
# compile directory, because that is how a course receives them: `kit materials
# sync` assembles a flat _materials/ tree next to the unit being built. This
# Makefile assembles the same tree into build/ and compiles there, so what is
# tested here is the arrangement that actually ships — not a convenient one
# that only works inside the kit.
#
# One Makefile for both: slidegen and sheetgen each carried a copy, identical
# but for the target, and the fonts and brand assets they both bundled are now
# shared rather than duplicated.
TEX   := xelatex   # := not ?=, so a stray TEX in the environment cannot pick the wrong engine
BUILD := ../build/materials
KIT   := ../..

all: slides worksheet

$(BUILD)/.assembled: beamerthemeboulingua.sty boulingua-sheet.sty
	@mkdir -p $(BUILD)/fonts $(BUILD)/brand/icons $(BUILD)/assets
	@cp *.sty *.tex                  $(BUILD)/
	@cp $(KIT)/kit/fonts/*.ttf       $(BUILD)/fonts/
	@cp $(KIT)/kit/brand/icons/*.pdf $(BUILD)/brand/icons/
	@cp $(KIT)/kit/brand/boulingua-logo.png $(BUILD)/assets/
	@touch $@

slides: $(BUILD)/.assembled
	cd $(BUILD) && $(TEX) -interaction=nonstopmode slides-template.tex >/dev/null
	cd $(BUILD) && $(TEX) -interaction=nonstopmode slides-template.tex >/dev/null
	@echo "  slides-template.pdf  -> $(BUILD)"

worksheet: $(BUILD)/.assembled
	cd $(BUILD) && $(TEX) -interaction=nonstopmode worksheet-template.tex >/dev/null
	cd $(BUILD) && $(TEX) -interaction=nonstopmode worksheet-template.tex >/dev/null
	@echo "  worksheet-template.pdf -> $(BUILD)"

clean:
	rm -rf $(BUILD)

.PHONY: all slides worksheet clean
