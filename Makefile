README.rst: README.md
	pandoc --from=markdown --to=rst --output=README.rst README.md

test: README.rst
	python dsnparse_test.py

tox: README.rst
	tox

package: README.rst
	python setup.py bdist_wheel --universal

clean:
	rm -rvf build/ dist/
