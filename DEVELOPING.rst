Release procedure
*****************

Before releasing, check
https://github.com/IAMconsortium/nomenclature/actions/workflows/pytest.yml to ensure
that the push and scheduled builds are passing. Address any failures before releasing.

1. Test if the build runs locally, by running ``python -m build --sdist --wheel --outdir dist/ ``. Fix any errors by creating a PR.

2. Tag the release candidate (RC) version on the main branch after fixing any packaging
   issues, with a ``rc<N>`` suffix, and push::

    $ git tag v<release version>rc<N>>
    $ git push upstream v<release version>rc<N>>

3. Check that the GitHub action "Publish to PyPI and TestPyPI" was executed correctly
   and that the release candidate was successfully uploaded to TestPyPI
   (https://test.pypi.org/project/nomenclature-iamc/).

4. (Optional) Create a fresh virtual environment, download the release from TestPyPi and
   check that tests are passing.
   In order to install correctly from TestPypi use the following:
   
   .. code-block:: python

   pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple nomenclature-iamc


5. Visit https://github.com/IAMconsortium/nomenclature/releases and mark the new release: either using the pushed tag from (5), or by creating the tag and release simultaneously.

6. Check at https://github.com/IAMconsortium/nomenclature/actions/workflows/publish.yaml and https://test.pypi.org/project/nomenclature-iamc/ that the distributions are published.

7. Confirm that the doc pages are updated on https://nomenclature-iamc.readthedocs.io/en/stable/

    - Both the latest and the stable versions point to the new release
    - The new release has been added to the list of available versions

