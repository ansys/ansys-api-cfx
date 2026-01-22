### ansys-api-cfx gRPC Interface Package

This Python package contains the auto-generated gRPC Python interface files for
CFX.

#### Installation

Provided that these wheels have been published to the public PyPI, they can be
installed with:

```
pip install ansys-api-cfx
```

#### Build

To build the gRPC packages, run:

```
pip install build
python -m build
```

This will create the source distribution and the wheel containing the protofiles and Python
interface files.

#### Manual Deployment

PyAnsys repositories have been moving to using the
trusted publisher approach when releasing to PyPI.
Because of this, manual deployment is no longer possible.

#### Automatic Deployment

This repository uses GitHub CI/CD to enable the automatic building of
source and wheel packages for these gRPC Python interface files. By default,
these are built on pull requests, the main branch, and on tags when pushing. Artifacts
are uploaded for each pull request.

To publicly release wheels to PyPI, ensure your branch is up-to-date and then
push tags. For example, for the version `v0.5.0`:

```bash
git tag v0.5.0
git push --tags
```
