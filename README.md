# Docker repository copy

A command-line interface to copy docker images between two repositories.

## Installation

```shell
pip install git+https://github.com/smassonnet/docker-repo-cp.git@main
```

## Usage

The following command will copy all tags from `ORG/IMAGE` (Docker HUB)
into a private registry hosted at `REGISTRY:5000`.

```shell
docker-repo-cp ORG/IMAGE REGISTRY:5000/ORG/IMAGE --apply
# Or
python -m docker_repo_cp ORG/IMAGE REGISTRY:5000/ORG/IMAGE --apply
```

When not specifying the `--apply` option, the command will not push the new image tags.
