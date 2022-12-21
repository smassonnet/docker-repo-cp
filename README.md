# Docker repository copy

A command-line interface to copy docker images between two repositories.

## Installation

```shell
pip install git+https://github.com/smassonnet/docker-repo-cp.git@main
```

## Usage

The following command will copy all tags from `my-organisation/my-image` (Docker HUB)
into a private registry hosted at `my-registry:5000`.

```shell
docker-repo-cp my-organisation/my-image my-registry:5000/my-organisation/my-image --apply
# Or
python -m docker_repo_cp my-organisation/my-image my-registry:5000/my-organisation/my-image --apply
```

When not specifying the `--apply` option, the command will not push the new image tags.
