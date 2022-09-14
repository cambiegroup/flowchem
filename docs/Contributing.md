# Contribute to flowchem
% part of this page is based on the numpy project one

Not a coder? Not a problem! Flowchem is multi-faceted, and we can use a lot of help.
These are all activities we’d like to get help with (they’re all important, so we list them in alphabetical order):

    Code maintenance and development

    Community coordination

    Developing educational content & narrative documentation

    Writing technical documentation

The rest of this document discusses working on the flowchem code base and documentation.

## Development process
If you are a first-time contributor:

* Go to [flowchem github repository](https://github.com/cambiegroup/flowchem) and click the “fork” button to create your own copy of the project.

* Clone the project to your local computer:

* `git clone https://github.com/your-username/flowchem.git`

* Change the directory:

* cd flowchem

* Add the upstream repository:

* git remote add upstream https://github.com/cambiegroup/flowchem.git

* Now, git `remote -v` will show two remote repositories named:
  * `upstream`, which refers to the `flowchem` repository
  * `origin`, which refers to your personal fork

* Develop your contribution:

* Pull the latest changes from upstream:

* `git checkout main`
* `git pull upstream main`

* Create a branch for the feature you want to work on. Since the branch name will appear in the merge message, use a sensible name such as ‘add-extendible-ear-support’:

* `git checkout -b add-extendible-ear-support`

* Commit locally as you progress (`git add` and `git commit`) Use a properly formatted commit message, write tests that fail before your change and pass afterward, run all the tests locally. Be sure to document any changed behavior in docstrings, keeping to the [Google docstring standard](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html).

* To submit your contribution:

* Push your changes back to your fork on GitHub:

* `git push origin add-extendible-ear-support`

* Enter your GitHub username and password (repeat contributors or advanced users can remove this step by connecting to GitHub with SSH).

* Go to GitHub. The new branch will show up with a green Pull Request button. Make sure the title and message are clear, concise, and self-explanatory. Then click the button to submit it.

* If your commit introduces a new feature or changes functionality, creat an issue on the GitHub repo to explain your changes. For bug fixes, documentation updates, etc., this is generally not necessary, though if you do not get any reaction, do feel free to ask for review.

* Review process:

* Reviewers (the other developers and interested community members) will write inline and/or general comments on your Pull Request (PR) to help you improve its implementation, documentation and style. Every single developer working on the project has their code reviewed, and we’ve come to see it as friendly conversation from which we all learn and the overall code quality benefits. Therefore, please don’t let the review discourage you from contributing: its only aim is to improve the quality of project, not to criticize (we are, after all, very grateful for the time you’re donating!). See our Reviewer Guidelines for more information.

* To update your PR, make your changes on your local repository, commit, run tests, and only if they succeed push to your fork. As soon as those changes are pushed up (to the same branch as before) the PR will update automatically. If you have no idea how to fix the test failures, you may push your changes anyway and ask for help in a PR comment.

Various continuous integration (CI) services are triggered after each PR update to build the code, run unit tests, measure code coverage and check coding style of your branch. The CI tests must pass before your PR can be merged. If CI fails, you can find out why by clicking on the “failed” icon (red cross) and inspecting the build and test log. To avoid overuse and waste of this resource, test your work locally before committing.

A PR must be approved by at least one core team member before merging. Approval means the core team member has carefully reviewed the changes, and the PR is ready for merging.

Document changes

Beyond changes to a functions docstring and possible description in the general documentation, if your change introduces any user-facing modifications they may need to be mentioned in the release notes. To add your change to the release notes, you need to create a short file with a summary and place it in doc/release/upcoming_changes. The file doc/release/upcoming_changes/README.rst details the format and filename conventions.

If your change introduces a deprecation, make sure to discuss this first on GitHub or the mailing list first. If agreement on the deprecation is reached, follow NEP 23 deprecation policy to add the deprecation.

Cross referencing issues

If the PR relates to any issues, you can add the text xref gh-xxxx where xxxx is the number of the issue to github comments. Likewise, if the PR solves an issue, replace the xref with closes, fixes or any of the other flavors github accepts.

In the source code, be sure to preface any issue or PR reference with gh-xxxx.


It is great that you are interested in contributing to the project!
Feel free to open issue/PR in the repo, but if you intend to introduce significant changes it is suggested to discuss it
in an issue before submitting a large pull request.

We target Python 3.10+ with src layout.

We use pre-commit for formatters/linter and tox for testing (pytest with coverage and mypy).
Both are run by CI (GitHub Actions) on every commit/PR.

src-layour
https://setuptools.pypa.io/en/latest/userguide/package_discovery.html#src-layout

```{toctree}
:maxdepth: 2
:caption: "Contents:"

DesignPrinciples
Add_new_device_type
models/Models

```
