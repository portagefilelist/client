# How to contribute to pfl

This project does use the [master branch][masterbranch] as the currently released version.
The [develop branch][developbranch] is the main branch for improvements and workplace for a future version.

Always write a clear log message for your commits. One-line messages are fine for small changes, but bigger changes should look like this:

    $ git commit -m "A brief summary of the commit
    >
    > A paragraph describing what changed and its impact."

## Did you find a bug?

* Use the [master branch][masterbranch] as a base for your pull request.
* **Ensure the bug was not already reported** by searching on GitHub under [Issues](https://github.com/portagefilelist/client/issues).
* If you're unable to find an open issue addressing the problem, [open a new one](https://github.com/portagefilelist/client/issues/new). Be sure to include a **title and clear description**, as much relevant information as possible, and a **code sample** or an **executable test case** demonstrating the expected behavior that is not occurring.

## Did you write a patch that fixes a bug?

* Use the [master branch][masterbranch] as a base for your pull request.
* Open a new GitHub pull request with the patch.
* Ensure the PR description clearly describes the problem and solution. Include the relevant issue number if applicable.

## Did you fix whitespace, format code, or make a purely cosmetic patch?

Changes that are cosmetic in nature and do not add anything substantial to the stability, functionality, or testability
will generally not be accepted.

## Do you intend to add a new feature or change an existing one?

* **You need to use the [develop branch][developbranch] as a base to make a GitHub pull request about a feature or improvement.**
* Open a GitHub pull request based on the [develop branch][developbranch] and include a **title and clear description** also as much relevant information as possible to clearly describe your intentions.
* Any GitHub pull request will be reviewed carefully. Please be patient, sometimes it can take some time to respond.

## Coding conventions

Start reading the code and you'll get the hang of it. The code is optimized for readability.

[masterbranch]: https://github.com/portagefilelist/client/tree/master
[developbranch]: https://github.com/portagefilelist/client/tree/develop
