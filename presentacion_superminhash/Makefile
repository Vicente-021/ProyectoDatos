LATEXFLAGS = -interaction=nonstopmode -halt-on-error
LATEX = pdflatex $(LATEXFLAGS)

all: main.pdf

main.pdf: main.tex data/alpha.dat
	latexmk -pdf $(LATEXFLAGS) main.tex

data/alpha.dat: scripts/gen_alpha.py
	python3 scripts/gen_alpha.py

notas: main_notas.pdf

main_notas.pdf: main.tex data/alpha.dat
	$(LATEX) -jobname=main_notas "\def\withnotes{1}\input{main.tex}"
	$(LATEX) -jobname=main_notas "\def\withnotes{1}\input{main.tex}"

clean:
	latexmk -C main.tex
	rm -f main_notas.pdf main_notas.aux main_notas.log main_notas.nav \
	      main_notas.out main_notas.snm main_notas.toc

.PHONY: all notas clean
