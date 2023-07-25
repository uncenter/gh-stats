#!/usr/bin/env python3

import aiohttp
import asyncio
import os
import pendulum
from typing import Dict, List, Optional, Set, Any, cast, Tuple
from dataclasses import dataclass


@dataclass
class Options:
    excluded_repos: Optional[Set] = None
    excluded_langs: Optional[Set] = None
    exclude_forked_repos: bool = False
    exclude_private_repos: bool = False


@dataclass
class GitHubAPI:
    access_token: str
    session: aiohttp.ClientSession
    semaphore = asyncio.Semaphore(10)

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

    async def query_graphql(self, query: str) -> Dict:
        try:
            async with self.semaphore:
                async with self.session.post(
                    "https://api.github.com/graphql",
                    headers=self.headers,
                    json={"query": query},
                ) as response:
                    result = await response.json()
                    return result if result else {}
        except aiohttp.ClientError as e:
            print(f"GQL query failed: {e}")
            return {}

    async def query_rest(self, path: str) -> Dict:
        for _ in range(60):
            if path.startswith("/"):
                path = path[1:]
            try:
                async with self.semaphore:
                    response = await self.session.get(
                        f"https://api.github.com/{path}",
                        headers=self.headers,
                    )
                if response.status == 202:
                    print(f"A path returned 202 ({path}). Retrying...")
                    await asyncio.sleep(2)
                    continue

                result = await response.json()
                if result is not None:
                    return result
            except aiohttp.ClientError:
                print("Request failed. Retrying...")
                await asyncio.sleep(2)
                continue

        print("There were too many 202s. Data for this repository will be incomplete.")
        return dict()


class Queries:
    @staticmethod
    def overview(
        options: Options,
        contrib_cursor: Optional[str] = None,
        owned_cursor: Optional[str] = None,
    ) -> str:
        """
        Get overall stats for a user.
        """

        return f"""{{
    viewer {{
        login,
        name,
        createdAt,
        followers {{
            totalCount
        }},
        following {{
            totalCount
        }},
        sponsoring {{
            totalCount
        }},
        starredRepositories {{
            totalCount
        }},
        repositories(
            {"privacy: PUBLIC," if options.exclude_private_repos else ""}
            first: 100,
            orderBy: {{
                field: UPDATED_AT,
                direction: DESC
            }},
            isFork: false,
            ownerAffiliations: [OWNER, ORGANIZATION_MEMBER],
            after: {"null" if owned_cursor is None else '"'+ owned_cursor +'"'}
        ) {{
            pageInfo {{
                hasNextPage
                endCursor
            }}
            nodes {{
                nameWithOwner
                stargazers {{
                    totalCount
                }}
                forkCount
                languages(first: 10, orderBy: {{field: SIZE, direction: DESC}}) {{
                    edges {{
                        size
                        node {{
                            name
                            color
                        }}
                    }}
                }}
            }}
        }}
        repositoriesContributedTo(
            first: 100,
            includeUserRepositories: false,
            orderBy: {{
                field: UPDATED_AT,
                direction: DESC
            }},
            contributionTypes: [
                COMMIT,
                PULL_REQUEST,
                REPOSITORY,
                PULL_REQUEST_REVIEW
            ]
            after: {"null" if contrib_cursor is None else '"'+ contrib_cursor +'"'}
        ) {{
            pageInfo {{
                hasNextPage
                endCursor
            }}
            nodes {{
                nameWithOwner
                stargazers {{
                    totalCount
                }}
                forkCount
                languages(first: 10, orderBy: {{field: SIZE, direction: DESC}}) {{
                    edges {{
                        size
                        node {{
                            name
                            color
                        }}
                    }}
                }}
            }}
        }}
    }}
}}"""

    @staticmethod
    def contribution_years() -> str:
        """
        Get the years for which a user has contributions.
        """

        return """
query {
    viewer {
        contributionsCollection {
            contributionYears
        }
    }
}
"""

    @staticmethod
    def contributions_by_year(year: str) -> str:
        """
        Generate a portion of a GraphQL query that retrieves the total contributions for a given year.
        """

        return f"""
    year{year}: contributionsCollection(
        from: "{year}-01-01T00:00:00Z",
        to: "{int(year) + 1}-01-01T00:00:00Z"
    ) {{
        contributionCalendar {{
            totalContributions
        }}
    }}
"""

    @classmethod
    def all_contributions(cls, years: List[str]) -> str:
        """
        Get all contributions from provided list of years.
        """

        by_years = "\n".join(map(cls.contributions_by_year, years))
        return f"""
query {{
    viewer {{
        {by_years}
    }}
}}
"""


class Stats:
    def __init__(
        self,
        username: str,
        access_token: str,
        session: aiohttp.ClientSession,
        options: Options,
    ):
        self.api = GitHubAPI(access_token=access_token, session=session)
        self.options = options
        self.username = username

        self._name: Optional[str] = None
        self._joined: Optional[pendulum.datetime] = None
        self._followers: Optional[int] = None
        self._following: Optional[int] = None
        self._sponsoring: Optional[int] = None
        self._starred_repositories: Optional[int] = None
        self._stargazers: Optional[int] = None
        self._forks: Optional[int] = None
        self._total_contributions: Optional[int] = None
        self._languages: Optional[Dict[str, Any]] = None
        self._repositories: Optional[Set[str]] = None
        self._lines_changed: Optional[Tuple[int, int]] = None

    async def get(self) -> None:
        """
        Get statistics about GitHub usage.
        """

        self._stargazers = 0
        self._forks = 0
        self._languages = dict()
        self._repositories = set()

        next_owned = None
        next_contrib = None
        while True:
            raw_results = (
                await self.api.query_graphql(
                    Queries.overview(
                        owned_cursor=next_owned,
                        contrib_cursor=next_contrib,
                        options=self.options,
                    )
                )
                or {}
            )

            self._name = raw_results.get("data", {}).get("viewer", {}).get("name", None)
            if self._name is None:
                self._name = (
                    raw_results.get("data", {})
                    .get("viewer", {})
                    .get("login", "No Name")
                )

            created_at = (
                raw_results.get("data", {}).get("viewer", {}).get("createdAt", None)
            )
            if created_at is not None:
                self._joined = pendulum.parse(created_at)

            self._followers = (
                raw_results.get("data", {})
                .get("viewer", {})
                .get("followers", {})
                .get("totalCount", 0)
            )
            self._following = (
                raw_results.get("data", {})
                .get("viewer", {})
                .get("following", {})
                .get("totalCount", 0)
            )
            self._sponsoring = (
                raw_results.get("data", {})
                .get("viewer", {})
                .get("sponsoring", {})
                .get("totalCount", 0)
            )
            self._starred_repositories = (
                raw_results.get("data", {})
                .get("viewer", {})
                .get("starredRepositories", {})
                .get("totalCount", 0)
            )

            contrib_repositories = (
                raw_results.get("data", {})
                .get("viewer", {})
                .get("repositoriesContributedTo", {})
            )
            owned_repositories = (
                raw_results.get("data", {}).get("viewer", {}).get("repositories", {})
            )

            repos = owned_repositories.get("nodes", [])
            if not self.options.exclude_forked_repos:
                repos += contrib_repositories.get("nodes", [])

            for repo in repos:
                if repo is None:
                    continue
                name = repo.get("nameWithOwner")
                if name in self._repositories or name in self.options.excluded_repos:
                    continue
                self._repositories.add(name)
                self._stargazers += repo.get("stargazers").get("totalCount", 0)
                self._forks += repo.get("forkCount", 0)

                for lang in repo.get("languages", {}).get("edges", []):
                    name = lang.get("node", {}).get("name", "Other")
                    languages = await self.languages
                    if name.lower() in {x.lower() for x in self.options.excluded_langs}:
                        continue
                    if name in languages:
                        languages[name]["size"] += lang.get("size", 0)
                        languages[name]["occurrences"] += 1
                    else:
                        languages[name] = {
                            "size": lang.get("size", 0),
                            "occurrences": 1,
                            "color": lang.get("node", {}).get("color"),
                        }

            if owned_repositories.get("pageInfo", {}).get(
                "hasNextPage", False
            ) or contrib_repositories.get("pageInfo", {}).get("hasNextPage", False):
                next_owned = owned_repositories.get("pageInfo", {}).get(
                    "endCursor", next_owned
                )
                next_contrib = contrib_repositories.get("pageInfo", {}).get(
                    "endCursor", next_contrib
                )
            else:
                break

        langs_total = sum([v.get("size", 0) for v in self._languages.values()])
        for k, v in self._languages.items():
            v["prop"] = 100 * (v.get("size", 0) / langs_total)

    @property
    async def name(self) -> str:
        """
        str: user's name/username
        """

        if self._name is not None:
            return self._name
        await self.get()
        assert self._name is not None
        return self._name

    @property
    async def joined(self) -> pendulum.datetime:
        """
        pendulum.datetime: when the user joined GitHub
        """

        if self._joined is not None:
            return self._joined
        await self.get()
        assert self._joined is not None
        return self._joined

    @property
    async def followers(self) -> int:
        """
        int: total number of followers
        """

        if self._followers is not None:
            return self._followers
        await self.get()
        assert self._followers is not None
        return self._followers

    @property
    async def following(self) -> int:
        """
        int: total number of users followed by user
        """

        if self._following is not None:
            return self._following
        await self.get()
        assert self._following is not None
        return self._following

    @property
    async def sponsoring(self) -> int:
        """
        int: total number of users and organizations sponsored by user
        """

        if self._sponsoring is not None:
            return self._sponsoring
        await self.get()
        assert self._sponsoring is not None
        return self._sponsoring

    @property
    async def starred_repositories(self) -> int:
        """
        int: total number of repositories starred by user
        """

        if self._starred_repositories is not None:
            return self._starred_repositories
        await self.get()
        assert self._starred_repositories is not None
        return self._starred_repositories

    @property
    async def stargazers(self) -> int:
        """
        int: total number of stargazers on user's repositories
        """

        if self._stargazers is not None:
            return self._stargazers
        await self.get()
        assert self._stargazers is not None
        return self._stargazers

    @property
    async def forks(self) -> int:
        """
        int: total number of forks on user's repositories
        """

        if self._forks is not None:
            return self._forks
        await self.get()
        assert self._forks is not None
        return self._forks

    @property
    async def languages(self) -> Dict:
        """
        Dict: summary of languages used by the user
        """

        if self._languages is not None:
            return self._languages
        await self.get()
        assert self._languages is not None
        return self._languages

    @property
    async def languages_proportional(self) -> Dict:
        """
        Dict: summary of languages used by the user, with proportional usage
        """

        if self._languages is None:
            await self.get()
            assert self._languages is not None

        return {k: v.get("prop", 0) for (k, v) in self._languages.items()}

    @property
    async def repositories(self) -> Set[str]:
        """
        Set[str]: list of names of user's repositories
        """

        if self._repositories is not None:
            return self._repositories
        await self.get()
        assert self._repositories is not None
        return self._repositories

    @property
    async def total_contributions(self) -> int:
        """
        int: count of user's total contributions as defined by GitHub
        """

        if self._total_contributions is not None:
            return self._total_contributions

        self._total_contributions = 0
        years = (
            (await self.api.query_graphql(Queries.contribution_years()))
            .get("data", {})
            .get("viewer", {})
            .get("contributionsCollection", {})
            .get("contributionYears", [])
        )
        by_year = (
            (await self.api.query_graphql(Queries.all_contributions(years)))
            .get("data", {})
            .get("viewer", {})
            .values()
        )
        for year in by_year:
            self._total_contributions += year.get("contributionCalendar", {}).get(
                "totalContributions", 0
            )
        return cast(int, self._total_contributions)

    @property
    async def lines_changed(self) -> Tuple[int, int]:
        """
        Tuple[int, int]: count of lines added and deleted by the user (Tuple[additions, deletions])
        """

        if self._lines_changed is not None:
            return self._lines_changed
        additions = 0
        deletions = 0
        for repo in await self.repositories:
            r = await self.api.query_rest(f"/repos/{repo}/stats/contributors")
            for author_obj in r:
                if not isinstance(author_obj, dict) or not isinstance(
                    author_obj.get("author", {}), dict
                ):
                    continue
                author = author_obj.get("author", {}).get("login", "")
                if author != self.username:
                    continue

                for week in author_obj.get("weeks", []):
                    additions += week.get("a", 0)
                    deletions += week.get("d", 0)

        self._lines_changed = (additions, deletions)
        return self._lines_changed


async def main() -> None:
    access_token = os.getenv("ACCESS_TOKEN")
    user = os.getenv("GITHUB_ACTOR")
    if access_token is None or user is None:
        raise RuntimeError(
            "ACCESS_TOKEN and GITHUB_ACTOR environment variables cannot be None!"
        )

    async with aiohttp.ClientSession() as session:
        github_api = GitHubAPI(access_token, session)
        stats = Stats(user, access_token, github_api)
        await stats.get()


if __name__ == "__main__":
    asyncio.run(main())
