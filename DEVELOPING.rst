Release procedure
*****************

0. Before releasing, check that the "pytest" GitHub action on the current "main" branch
   passes. Address any failures before releasing.

1. Test on your local machine if the build runs by running ``python -m build --sdist
   --wheel --outdir dist/``. Fix any packaging issues or errors by creating a PR.

2. Tag the release candidate (RC) version on the main branch as ``v<release
   version>rc<N>`` and push to upstream::

   $ git tag v<release version>rc<N>>
   $ git push upstream v<release version>rc<N>

3. Check that the GitHub action "Publish to PyPI and TestPyPI" was executed correctly
   and that the release candidate was successfully uploaded to TestPyPI. The address
   will be https://test.pypi.org/project/nomenclature-iamc/<release version>rc<N>/.
   E.g.: https://test.pypi.org/project/nomenclature-iamc/0.5rc1/

4. (Optional) Create a fresh virtual environment, download the release from TestPyPi and
   check that the install of package has worked correctly::
   
   $ pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple nomenclature-iamc==v<release version>rc<N>

5. Visit https://github.com/IAMconsortium/nomenclature/releases and mark the new release
   by creating the tag and release simultaneously. The name of the tag is v<release
   version> (without the rc<N>). 

6. Check that the "Publish to PyPI and TestPyPI" GitHub action passed and that the
   distributions are published on https://pypi.org/project/nomenclature-iamc/ .

7. Confirm that the doc pages are updated on
   https://nomenclature-iamc.readthedocs.io/en/stable/:

   - Both the latest and the stable versions point to the new release
   - The new release has been added to the list of available versions

8. Confirm that the zenodo entry is updated on https://doi.org/10.5281/zenodo.5930653.
