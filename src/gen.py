#!/usr/bin/python3

import os
import json
import aiohttp
import asyncio
from typing import Dict

from stats import Stats, Options

DIRNAME = os.path.realpath(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(DIRNAME, "templates")
OUTPUT_DIR = os.path.join(DIRNAME, "..", "dist")


def replace_with_data(data: Dict[str, str], content: str) -> str:
    """
    Replace placeholder strings in a template with associated data.

    Args:
        data (dict[str, str]): A dictionary of placeholder strings and their associated data.
        content (str): The template content.

    Returns:
        str: The template content with the placeholder strings replaced.
    """

    for key, value in data.items():
        content = content.replace("{{ " + key + " }}", value)
    return content


def load_json(file: str) -> Dict:
    """
    Load data from a JSON file.

    Args:
        file (str): Path to the JSON file.

    Returns:
        dict: Parsed JSON data.
    """

    with open(file, "r") as f:
        data = json.load(f)
    return data


def get_inserted_styles() -> Dict[str, Dict[str, str]]:
    """
    Convert template styles from JSON to CSS properties, themed for light and dark mode.

    Returns:
        dict[str, dict[str, str]]: A dictionary with two keys, "light" and "dark", each containing a dictionary of theme-specific CSS properties.
    """

    raw_styles = load_json(os.path.join(TEMPLATE_DIR, "styles.json"))

    dark_styles = {}
    light_styles = {}
    for key, value in raw_styles.items():
        _selector = value.get("selector")
        _properties = value.get("properties")
        _both = (
            (_properties.get("both").items())
            if _properties.get("both") is not None
            else {}
        )
        _light = (
            (_properties.get("light").items())
            if _properties.get("light") is not None
            else {}
        )
        _dark = (
            (_properties.get("dark").items())
            if _properties.get("dark") is not None
            else {}
        )
        if _selector is not False:
            _both_properties = "".join([f"\t{prop}: {val};\n" for prop, val in _both])
            _light_properties = "".join([f"\t{prop}: {val};\n" for prop, val in _light])
            _dark_properties = "".join([f"\t{prop}: {val};\n" for prop, val in _dark])
            light_styles[
                key
            ] = f"{_selector} {{\n{_both_properties}{_light_properties}}}"
            dark_styles[key] = f"{_selector} {{\n{_both_properties}{_dark_properties}}}"

        for prop, val in _light:
            light_styles[f"{key}.{prop}"] = val
        for prop, val in _dark:
            dark_styles[f"{key}.{prop}"] = val
        for prop, val in _both:
            light_styles[f"{key}.{prop}"] = val
            dark_styles[f"{key}.{prop}"] = val

    return {
        "light": {f"styles.{key}": value for key, value in light_styles.items()},
        "dark": {f"styles.{key}": value for key, value in dark_styles.items()},
    }


async def generate_image(template_name: str, s: Stats, output_path: str) -> None:
    """
    Generate an image based on the given template.

    Args:
        template_name (str): Name of the template.
        s (Stats): Stats object.
        output_path (str): Output path for the generated image.
    """

    with open(os.path.join(TEMPLATE_DIR, f"{template_name}.svg"), "r") as f:
        template = f.read()

    replacements = {
        "name": await s.name,
        "joined_relative": (await s.joined).relative,
        "joined_formatted": (await s.joined).formatted,
        "followers": f"{await s.followers:,}",
        "following": f"{await s.following:,}",
        "sponsoring": f"{await s.sponsoring:,}",
        "starred_repositories": f"{await s.starred_repositories:,}",
        "stargazers": f"{await s.stargazers:,}",
        "forks": f"{await s.forks:,}",
        "contributions": f"{await s.total_contributions:,}",
        "lines_changed": f"{((await s.lines_changed)[0] + (await s.lines_changed)[1]):,}",
        "repository_count": f"{len(await s.repositories):,}",
    }

    if template_name == "languages":
        sorted_languages = sorted(
            (await s.languages).items(), reverse=True, key=lambda t: t[1].get("size")
        )[:8]
        print(sorted_languages)

        progress = "".join(
            f'<span style="background-color: {data.get("color", "#000000")}; width: {data.get("prop", 0):0.3f}%;"></span>'
            for lang, data in sorted_languages
        )

        lang_list = "".join(
            f"""<li>
<svg xmlns="http://www.w3.org/2000/svg" class="octicon" style="fill:{data.get("color", "#000000")};" viewBox="0 0 16 16" width="16" height="16"><circle xmlns="http://www.w3.org/2000/svg" cx="8" cy="9" r="5" /></svg>
<span class="lang">{lang}</span>
<span class="percent">{data.get("prop", 0):0.2f}%</span>
</li>"""
            for lang, data in sorted_languages
        )

        replacements.update({"progress": progress, "lang_list": lang_list})
    print(replacements)
    output = replace_with_data(replacements, template)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for theme in ["light", "dark"]:
        with open(
            os.path.join(
                OUTPUT_DIR,
                replace_with_data(
                    {"theme": theme, "template": template_name}, output_path
                ),
            ),
            "w",
        ) as f:
            f.write(replace_with_data(get_inserted_styles()[theme], output))


async def main() -> None:
    def string_to_list(string) -> list:
        """
        Convert a comma-separated string to a list of strings.

        Args:
            string (str): A comma-separated string.

        Returns:
            list: A list of strings.
        """

        return [x.strip() for x in string.split(",")] if string else []

    def truthy(value, default=False) -> bool:
        """
        Convert an unknown value to a boolean.

        Args:
            value (str, int, bool): An unknown value.

        Returns:
            bool: The boolean representation of the value.
        """

        if isinstance(value, str):
            return value.strip().lower() in ["true", "1", "yes", "y"]
        elif isinstance(value, int):
            return value == 1
        elif isinstance(value, bool):
            return value
        return default

    access_token = os.getenv("ACCESS_TOKEN")
    if not access_token:
        raise Exception("A personal access token is required to proceed!")

    user = os.getenv("GITHUB_ACTOR")
    if user is None:
        raise RuntimeError("Environment variable GITHUB_ACTOR must be set.")

    options = Options(
        excluded_repos=string_to_list(os.getenv("EXCLUDED")),
        excluded_langs=string_to_list(os.getenv("EXCLUDED_LANGS")),
        exclude_forked_repos=truthy(os.getenv("EXCLUDE_FORKED_REPOS"), True),
        exclude_private_repos=truthy(os.getenv("EXCLUDE_PRIVATE_REPOS"), True),
    )

    generated_image_path = os.getenv("GENERATED_IMAGE_PATH")
    if generated_image_path is None or not generated_image_path.strip().endswith(
        ".svg"
    ):
        raise RuntimeError(
            "Environment variable GENERATED_IMAGE_PATH must be set and end with .svg"
        )

    async with aiohttp.ClientSession() as session:
        s = Stats(
            user,
            access_token,
            session,
            options,
        )

        await asyncio.gather(
            generate_image("languages", s, generated_image_path),
            generate_image("overview", s, generated_image_path),
            generate_image("community", s, generated_image_path),
        )


if __name__ == "__main__":
    asyncio.run(main())
