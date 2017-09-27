doc:
	pandoc --from=markdown --to=rst --output=README.rst README.md

test: doc
	python dsnparse_test.py

tox: doc
	tox

package:
	python setup.py bdist_wheel --universal

clean:
	rm -rvf build/ dist/
