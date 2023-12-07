from typing import List
from operations.schemas.object_schemas import StartUploadRequest


class PlacementPolicy:
    def __init__(self, init_regions: List[str] = []) -> None:
        self.init_regions = init_regions

    def place(self, req: StartUploadRequest) -> List[str]:
        pass

    def name(self) -> str:
        pass


class SingleRegionWrite(PlacementPolicy):
    """
    Write to the same region as the original storage region defined in the config
    """

    def __init__(self, init_regions: List[str]) -> None:
        super().__init__(init_regions)
        self.single_store_region = "aws:us-west-1"

    def place(self, req: StartUploadRequest) -> List[str]:
        """
        Args:
            req: StartUploadRequest
        Returns:
            List[str]: single region to write to
        """
        assert self.single_store_region in self.init_regions
        return [self.single_store_region]

    def name(self) -> str:
        return "single_region"


class ReplicateAll(PlacementPolicy):
    """
    Replicate all objects to all regions
    """

    def __init__(self, init_regions: List[str]) -> None:
        super().__init__(init_regions)

    def place(self, req: StartUploadRequest) -> List[str]:
        """
        Args:
            req: StartUploadRequest
        Returns:
            List[str]: all available regions in the current nodes graph
        """
        return self.init_regions

    def name(self) -> str:
        return "replicate_all"


class PushonWrite(PlacementPolicy):
    """
    Write local and push asynchronously to a set of pushed regions
    """

    def __init__(self, init_regions: List[str]) -> None:
        super().__init__(init_regions)
        self.push_regions = ["aws:us-west-1", "aws:us-east-1"]

    def place(
        self,
        req: StartUploadRequest,
    ) -> List[str]:
        """
        Args:
            req: StartUploadRequest
        Returns:
            List[str]: the regions to push to, including the primary region and the regions we want to push to
        """
        # assert all push regions in init_regions
        assert all(r in self.init_regions for r in self.push_regions)
        return list(set([req.client_from_region] + self.push_regions))

    def name(self) -> str:
        return "push"


class PullOnRead(PlacementPolicy):
    """
    Write local, and pull on read if data is not available locally
    """

    def place(self, req: StartUploadRequest) -> List[str]:
        """
        Args:
            req: StartUploadRequest
        Returns:
            List[str]: the region client is from
        """
        return [req.client_from_region]

    def name(self) -> str:
        return "copy_on_read"


class LocalWrite(PlacementPolicy):
    """
    Write to local region
    """

    def place(self, req: StartUploadRequest) -> List[str]:
        """
        Args:
            req: StartUploadRequest
        Returns:
            List[str]: the local region client is from
        """
        return [req.client_from_region]

    def name(self) -> str:
        return "write_local"


def get_placement_policy(name: str, init_regions: List[str]) -> PlacementPolicy:
    if name == "single_region":
        return SingleRegionWrite(init_regions)
    elif name == "replicate_all":
        return ReplicateAll(init_regions)
    elif name == "push":
        return PushonWrite(init_regions)
    elif name == "copy_on_read":
        return PullOnRead(init_regions)
    elif name == "write_local":
        return LocalWrite(init_regions)
    else:
        raise ValueError(f"Unknown policy name: {name}")
