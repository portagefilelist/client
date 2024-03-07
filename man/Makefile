all: pfl.1 e-file.1

pfl.1:
	pandoc --standalone --from markdown --to man pfl.1.md -o pfl.1

e-file.1:
	pandoc --standalone --from markdown --to man e-file.1.md -o e-file.1

clean:
	rm -f pfl.1
	rm -f e-file.1

