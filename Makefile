clean:
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info

build: clean
	python setup.py sdist

check: build
	twine check dist/*

upload: build
	twine upload dist/*

.PHONY: clean build check upload