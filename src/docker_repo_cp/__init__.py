import argparse
import dataclasses
import json
import logging
from contextlib import contextmanager
from typing import List, NamedTuple, Optional, Set, cast

import docker
from docker.models.images import Image as _DockerImage

logger = logging.getLogger(__name__)


class ImageTag(NamedTuple):
    repository: str
    tag: str

    @classmethod
    def from_string(cls, s: str):
        split_s = s.split(":")
        if len(split_s) < 2:
            raise ValueError(f"Invalid tag name: {s}")
        *image_name_parts, tag = split_s
        return cls(repository=":".join(image_name_parts), tag=tag)

    @property
    def uri(self):
        return f"{self.repository}:{self.tag}"


class Image(NamedTuple):
    id: str
    tags: List[ImageTag]
    docker_object: _DockerImage


def process_docker_push_logs(logs: str):
    for line in logs.split("\n"):
        if line:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                pass
            else:
                if "error" in payload:
                    raise ValueError(f"Pushing to registry raised an error: {payload}")


@dataclasses.dataclass
class DockerImageProxy:
    client: docker.DockerClient
    apply: bool = False

    def _format_docker_image(self, docker_image: _DockerImage) -> Image:
        return Image(
            id=cast(str, docker_image.id),
            tags=[ImageTag.from_string(t) for t in docker_image.tags],
            docker_object=docker_image,
        )

    def list(self, name: Optional[str] = None) -> List[Image]:
        image_list = cast(List[_DockerImage], self.client.images.list(name=name))
        return [self._format_docker_image(image) for image in image_list]

    def pull_all(self, repository_name: str) -> List[Image]:
        logger.info(f"Pulling images for repository {repository_name}")
        image_list = cast(
            List[_DockerImage], self.client.images.pull(repository_name, all_tags=True)
        )
        return [self._format_docker_image(image) for image in image_list]

    def migrate_tags(
        self, image: Image, src_repository: str, new_repository: str
    ) -> Image:
        """Creates a new image tag under the passed `new_repository`"""
        new_image_tags: List[ImageTag] = []
        for prev_tag in image.tags:
            if not prev_tag.repository.startswith(src_repository):
                # This is not a tag present in the source repository
                continue
            # Creating and saving new tag
            new_tag = ImageTag(repository=new_repository, tag=prev_tag.tag)
            logger.info(f"Tagging {prev_tag.uri} -> {new_tag.uri}")
            if self.apply:
                image.docker_object.tag(new_tag.repository, tag=new_tag.tag)
            new_image_tags.append(new_tag)

        return Image(
            id=image.id,
            tags=image.tags + new_image_tags,
            docker_object=image.docker_object,
        )

    def push_all(self, repository_name: str):
        logger.info(f"Pushing all images to repository {repository_name}")
        if self.apply:
            logs = self.client.images.push(repository_name)
            process_docker_push_logs(logs)


def list_local_images(
    client: docker.DockerClient, *args, **kwargs
) -> List[_DockerImage]:
    return cast(List[_DockerImage], client.images.list(*args, **kwargs))


@contextmanager
def docker_context(client: docker.DockerClient, apply: bool = False):
    init_image_tags = cast(
        Set[str], {tag for image in list_local_images(client) for tag in image.tags}
    )

    try:
        yield DockerImageProxy(client=client, apply=apply)
    finally:
        for image in list_local_images(client):
            for image_tag in image.tags:
                if image_tag in init_image_tags:
                    # No need to delete it
                    continue
                logger.info(f"Deleting image with tag: {image_tag}")
                client.images.remove(image_tag)


def main(src_repository: str, dst_repository: str, apply: bool = False):
    client = docker.from_env()

    with docker_context(client, apply=apply) as image_context:
        # Pulling images
        pulled_images = image_context.pull_all(src_repository)

        # Tagging images with the new repository
        for image in pulled_images:
            image_context.migrate_tags(image, src_repository, dst_repository)

        # Pushing to the new repository
        image_context.push_all(dst_repository)


def cli():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(
        "docker-repo-cp", description="CLI to copy docker images between repositories"
    )

    parser.add_argument(
        "src_repository", help="The repository to pull the source images"
    )
    parser.add_argument(
        "dst_repository", help="The repository to push the renamed images"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Performs the copy of images",
    )

    arguments = parser.parse_args()
    main(arguments.src_repository, arguments.dst_repository, apply=arguments.apply)
