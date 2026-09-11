================
Template package
================

To get started using this template, you should:

- Adapt package name in setup.py, CITATION.cff, docs/conf.py, docs/index.rst
- Adapt dependencies in setup.py, environment.yaml
- Choose a license and add it to LICENSE.txt
- Adapt README.rst

Installation
============

Install local repository in your environment:

    pip install -e <path to repo>

You can also point to the GitHub repository in your project's dependencies.
In conda environment.yaml:

   - pip
   - pip:
     - git+https://github.com/<repository>.git@<commit or tag id>

In virtualenv requirements.txt:

    -e git+https://github.com/<repository>.git@<commit or tag id>

Development
===========

Install dev dependencies:
    
    pip install template-package[dev]

Activate pre-commit hooks:

    pre-commit install

Docs
----

Minimal: Document usage in README.rst
Extended: Use sphinx docs, focus on API.

Build docs locally:
    
    cd docs
    make html

Release process
---------------

.. TODO: Describe release procedure.
- Adapt version in pyproject.toml
