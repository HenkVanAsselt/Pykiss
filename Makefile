# Makefile for Python KISS Module.

.DEFAULT_GOAL := all

all: develop

install_requirements:
	pip install -r requirements.txt

develop: remember
	python setup.py develop

install: remember
	python setup.py install

uninstall:
	pip uninstall -y pykiss

reinstall: uninstall install

remember:
	@echo --------------------------------------------------
	@echo "Hello from the Makefile..."
	@echo "Don't forget to run: 'make install_requirements'"
	@echo --------------------------------------------------

clean:
	@rm -R build dist .eggs *egg-info
	@rm -R .pytest_cache
	@rm -R kiss\__pycache__
	@rm -R lib\__pycache__
	@rm -R tests\__pycache__
	@rm -R doc\doxygen\build
	@rm -R doc\sphinx-autodoc\build

publish:
	python setup.py register sdist upload

nosetests: remember
	python setup.py nosetests

pep8: remember
	flake8 --max-complexity 12 --exit-zero kiss

flake8: pep8

lint: remember
	pylint --msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}" -r n --ignore-imports=y kiss 
	
pylint: lint

coverage:
	coverage report -m
	
test: lint pep8 nosetests coverage

pytest:
	py.test tests

sphinx:
	cd doc\sphinx-autodoc & make clean & make html & cd ...

doxygen:
	cd doc\doxygen & "C:\Program Files\doxygen\bin\doxygen.exe" & cd ...