"""Small provider-neutral GitHub REST transport.

No agent calls this transport directly. The broker invokes it only after AEGIS
has evaluated the requested action.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request


class GitHubTransportError(RuntimeError):
    pass


class GitHubRepositoryClient:
    def __init__(self, token: str, api_base: str = "https://api.github.com") -> None:
        if not token.strip():
            raise GitHubTransportError("GitHub token is required")
        self._token = token
        self._api_base = api_base.rstrip("/")

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        url = f"{self._api_base}{path}"
        data = None
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "HOARE-GitHub-Broker/1.0",
        }
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise GitHubTransportError(f"GitHub API {exc.code}: {detail[:1000]}") from exc
        except urllib.error.URLError as exc:
            raise GitHubTransportError(f"GitHub API unavailable: {exc}") from exc
        try:
            return json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise GitHubTransportError("GitHub API returned invalid JSON") from exc

    @staticmethod
    def _repo_path(repository: str) -> str:
        parts = repository.strip().split("/")
        if len(parts) != 2 or not all(parts):
            raise GitHubTransportError("repository must be owner/name")
        return "/repos/" + "/".join(urllib.parse.quote(part, safe="") for part in parts)

    def repository(self, repository: str) -> dict:
        return self._request("GET", self._repo_path(repository))

    def contents(self, repository: str, path: str = "", ref: str | None = None) -> dict | list:
        clean = path.strip("/")
        endpoint = self._repo_path(repository) + "/contents"
        if clean:
            endpoint += "/" + "/".join(urllib.parse.quote(part, safe="") for part in clean.split("/"))
        if ref:
            endpoint += "?ref=" + urllib.parse.quote(ref, safe="")
        return self._request("GET", endpoint)

    def create_branch(self, repository: str, branch: str, base_sha: str) -> dict:
        return self._request(
            "POST",
            self._repo_path(repository) + "/git/refs",
            {"ref": f"refs/heads/{branch}", "sha": base_sha},
        )

    def create_pull_request(
        self,
        repository: str,
        *,
        title: str,
        head: str,
        base: str,
        body: str = "",
    ) -> dict:
        return self._request(
            "POST",
            self._repo_path(repository) + "/pulls",
            {"title": title, "head": head, "base": base, "body": body},
        )

    def update_file(
        self,
        repository: str,
        path: str,
        *,
        content: str,
        message: str,
        branch: str,
        sha: str | None = None,
    ) -> dict:
        payload = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha
        endpoint = self._repo_path(repository) + "/contents/" + "/".join(
            urllib.parse.quote(part, safe="") for part in path.strip("/").split("/")
        )
        return self._request("PUT", endpoint, payload)


__all__ = ["GitHubRepositoryClient", "GitHubTransportError"]
