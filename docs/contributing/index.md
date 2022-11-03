# Contribute to flowchem
% part of this page is based on the numpy project one
% See also https://rdflib.readthedocs.io/en/stable/developers.html
% And https://diataxis.fr/how-to-guides/

Not a coder? Not a problem! Flowchem is multi-faceted, and we can use a lot of help.
These are all activities we’d like to get help with :

    Code maintenance and development

    Developing educational content & narrative documentation

    Writing technical documentation

The rest of this document discusses working on the flowchem code base and documentation.

## Development process
1. If you are a first-time contributor:

   * Go to [flowchem gitHub repository](https://github.com/cambiegroup/flowchem) and click the “fork” button to create your own copy of the project.

   * Clone the project to your local computer:

   * `git clone https://github.com/your-username/flowchem.git`

   * Change the directory:

   * cd flowchem

   * Add the upstream repository:

   * git remote add upstream https://github.com/cambiegroup/flowchem.git

   * Now, git `remote -v` will show two remote repositories named:
     * `upstream`, which refers to the `flowchem` repository
     * `origin`, which refers to your personal fork

2. Develop your contribution:

   * Pull the latest changes from upstream:

   * `git checkout main`
   * `git pull upstream main`

   * Create a branch for the feature you want to work on. Since the branch name will appear in the merge message, use a sensible name. For example, if you intend to add support for a new device type, called ExtendibleEar a good candidate could be ‘add-extendible-ear-support’:

   * `git checkout -b add-extendible-ear-support`

   * Commit locally as you progress (`git add` and `git commit`) Use a properly formatted commit message, write tests that fail before your change and pass afterward, run all the tests locally. Be sure to document any changed behavior in docstrings, keeping to the [Google docstring standard](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html).

3. To submit your contribution:

   * Push your changes back to your fork on GitHub:

   * `git push origin add-extendible-ear-support`

   * Enter your GitHub username and password (repeat contributors or advanced users can remove this step by connecting to GitHub with SSH).

   * Go to GitHub. The new branch will show up with a green Pull Request button. Make sure the title and message are clear, concise, and self-explanatory. Then click the button to submit it.

   * If your commit introduces a new feature or changes functionality, creat an issue on the GitHub repo to explain your changes. For bug fixes, documentation updates, etc., this is generally not necessary, though if you do not get any reaction, do feel free to ask for review.

4. Review process:

   * Reviewers (the other developers and interested community members) will write inline and/or general comments on your Pull Request (PR) to help you improve its implementation, documentation and style. We aim at protecting the main branch from direct commits to ensure all changes are introduced via pull requests that can be reviewed. The review is meant as friendly conversation from which we all learn and the overall code quality benefits. Please do not let the review discourage you from contributing: its only aim is to improve the quality of project, not to criticize (we are, after all, very grateful for your contribution!).

   * To update your PR, make your changes on your local repository, commit, run tests, and only if they succeed push to your fork. As soon as those changes are pushed up (to the same branch as before) the PR will update automatically. If you have no idea how to fix the test failures, you may push your changes anyway and ask for help in a PR comment.

   * Various continuous integration (CI) services are triggered after each PR update to build the code, run unit tests, measure code coverage and check coding style of your branch. The CI tests must pass before your PR can be merged. If CI fails, you can find out why by clicking on the “failed” icon (red cross) and inspecting the build and test log. To speed up this cycle you can also test your work locally before committing.

   * A PR which has been approved by at least one core team member will be merged in the main branch and will be part of the next release of flowchem.

5. Document changes

   * If your change introduces support for a new device make sure to add description for it in the docs and the README.

6. Cross-referencing issues

   * If the PR solves an issue, you can add the text closes xxxx, where xxxx is the number of the issue. Instead of closes you can use any of the other flavors [gitHub accepts](https://help.github.com/en/articles/closing-issues-using-keywords) such as fix and resolve.

## Guidelines

* All code should be documented with docstrings in Google format and comments where appropriate.
* All code should have tests.
* We use [black](https://github.com/psf/black) not to waste time discussing details code style.
* You can install [pre-commit](https://pre-commit.com/) to run black and other linters as part of the pre-commit hooks. See our `.pre-commit-config.yml` for details. The use of linter and import re-ordering is aimed at reducing diff size and merge conflicts in pull request.

## Test coverage
To run the tests `pytest` and some pytest plugins are needed. To install the testing-related dependency for local testing run this command from the root folder:
```shell
pip install .[test]
```

## Building docs
The docs are automatically build for each commit at [readthedocs.com](https://readthedocs.org/projects/flowchem/).
To build it locally, sphynx, myst-parser and other packages are needed. To install the tools to build the docs run this command from the root folder:
```shell
pip install .[docs]
```

Then from the docs folder run `make html` to generate html docs in the build directory.


```{toctree}
:maxdepth: 2

community
design_principles
add_device/index
models/device_models

```
