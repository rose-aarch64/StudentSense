import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


async def make_folder(client: AsyncClient, name: str = "2026/FA") -> int:
    """Create a folder and return its id."""
    return (await client.post("/workspace-folders", json={"name": name})).json()["id"]


async def make_workspace(client: AsyncClient, name: str = "Bio") -> int:
    """Create a workspace and return its id."""
    return (await client.post("/workspaces", json={"name": name})).json()["id"]


async def test_a_created_folder_is_listed_oldest_first(client: AsyncClient) -> None:
    """The rail keeps its folders in the order they were made."""
    created = await client.post("/workspace-folders", json={"name": "2026/FA"})
    await client.post("/workspace-folders", json={"name": "2026/SP"})

    assert created.status_code == 201
    listed = (await client.get("/workspace-folders")).json()
    assert [folder["name"] for folder in listed] == ["2026/FA", "2026/SP"]


async def test_a_folder_name_is_trimmed_and_cannot_be_blank_or_huge(
    client: AsyncClient,
) -> None:
    """A folder row of spaces would render as nothing."""
    trimmed = await client.post("/workspace-folders", json={"name": "  Fall  "})
    blank = await client.post("/workspace-folders", json={"name": "   "})
    huge = await client.post("/workspace-folders", json={"name": "x" * 201})

    assert trimmed.json()["name"] == "Fall"
    assert blank.status_code == 422
    assert huge.status_code == 422


async def test_a_folder_can_be_renamed_and_a_missing_one_is_not_found(
    client: AsyncClient,
) -> None:
    """Terms are renamed by Canvas, and by hand."""
    folder_id = await make_folder(client)

    renamed = await client.patch(
        f"/workspace-folders/{folder_id}", json={"name": "Fall"}
    )
    missing = await client.patch("/workspace-folders/999", json={"name": "Fall"})

    assert renamed.json()["name"] == "Fall"
    assert missing.status_code == 404


async def test_deleting_a_folder_keeps_its_workspaces_unfiled(
    client: AsyncClient,
) -> None:
    """A folder only groups; losing one must never lose a class."""
    folder_id = await make_folder(client)
    workspace_id = await make_workspace(client)
    await client.patch(f"/workspaces/{workspace_id}", json={"folder_id": folder_id})

    deleted = await client.delete(f"/workspace-folders/{folder_id}")

    assert deleted.status_code == 204
    workspace = (await client.get(f"/workspaces/{workspace_id}")).json()
    assert workspace["folder_id"] is None
    assert (await client.delete(f"/workspace-folders/{folder_id}")).status_code == 404
