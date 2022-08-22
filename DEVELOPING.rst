Release procedure
*****************

Before releasing, check https://github.com/IAMconsortium/nomenclature/actions/workflows/pytest.yml to ensure that the push and scheduled builds are passing.
Address any failures before releasing.

1. Create a new branch::

    $ git checkout -b release/v<release version>

2. Tag the release candidate (RC) version, i.e. with a ``rcN`` suffix, and push::

    $ git tag v<release version>rc<N>>
    $ git push --tags origin release/v<release version>

3. Open a PR with the title “Release v<release version>” using this branch.
   Check:

   - at https://github.com/IAMconsortium/nomenclature/actions/workflows/publish.yaml that the workflow completes: the package builds successfully and is published to TestPyPI.
   - at https://test.pypi.org/project/nomenclature-iamc/ that:

      - The package can be downloaded, installed and run.
      - The README is rendered correctly.

   Address any warnings or errors that appear.
   If needed, make a new commit and go back to step (2), incrementing the rc number.

4. Merge the PR using the ‘rebase and merge’ method.

5. (optional) Switch back to the ``main`` branch, tag the release itself (*without* an RC number) and push::

    $ git checkout main
    $ git pull --fast-forward
    $ git tag v<release version>
    $ git push --tags origin main

   This step (but *not* step (2)) can also be performed directly on GitHub; see (6), next.

6. Visit https://github.com/IAMconsortium/nomenclature/releases and mark the new release: either using the pushed tag from (5), or by creating the tag and release simultaneously.

7. Check at https://github.com/IAMconsortium/nomenclature/actions/workflows/publish.yaml and https://test.pypi.org/project/nomenclature-iamc/ that the distributions are published.

8. Confirm that the doc pages are updated on https://nomenclature-iamc.readthedocs.io/en/stable/

    - Both the latest and the stable versions point to the new release
    - The new release has been added to the list of available versions

