<h1>gh-stats</h1>

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square)](https://github.com/psf/black)

A workflow that generates various statistics about my GitHub activity in the form of SVGs. Check out the [original project (GitHub Stats Visualization)](https://github.com/jstrieb/github-stats) and [idiotWu's more updated fork](https://github.com/idiotWu/stats) that served as the basis for some of the changes I made.

| Dark                                                                                  | Light                                                                                  |
| ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| ![](https://raw.githubusercontent.com/uncenter/gh-stats/main/dist/overview-dark.svg)  | ![](https://raw.githubusercontent.com/uncenter/gh-stats/main/dist/overview-light.svg)  |
| ![](https://raw.githubusercontent.com/uncenter/gh-stats/main/dist/languages-dark.svg) | ![](https://raw.githubusercontent.com/uncenter/gh-stats/main/dist/languages-light.svg) |
| ![](https://raw.githubusercontent.com/uncenter/gh-stats/main/dist/community-dark.svg) | ![](https://raw.githubusercontent.com/uncenter/gh-stats/main/dist/community-light.svg) |

## Features

- No distracting animations
- Consistent styling and overall layout between images
- No gaps between colors in the languages progress bar
- Languages aligned in clean looking columns
- Larger color circles for each language label
- `EXCLUDE_PRIVATE_REPOS` option

## Usage

Clone this repository without the Git history and create a new GitHub repository for it.

```sh
git clone --depth 1 https://github.com/uncenter/gh-stats.git
```

Adjust settings/options via environment variables in `.github/workflows/main.yml` to your liking. You'll need to generate a personal access token for the workflow to succeed:

1. Click this link: [generate a new "classic" token](https://github.com/settings/tokens/new) (if you are not logged in, follow these [instructions](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token)).
2. Ensure you select "classic" token type.
3. Name the token.
4. STo use these options, add a new secret with the specified name and value to your repository's secrets, similar to how you added the access token secret. If you prefer not to use secrets, you can directly set the values in the workflow file by replacing VARIABLE_NAME: ${{ secrets.VARIABLE_NAME }} with the desired value (e.g., VARIABLE_NAME: true). For options that accept lists of values, ensure you provide the values as comma-separated strings within a single string.et your preferred 'Expiration' date (no expiration if you want to just "set and forget").
5. Select `repo` for full control of private repositories.
6. Select `read:user` for read-only access to all user profile data.
7. Click the 'Generate token' button.
8. Copy the generated token - this is the one and only time to copy it.

You'll then need to create a new repository secret for this token:

1. Go to the **Settings** tab of the repository, click the **Secrets and variables** item on the side panel, click **Actions** in the expanded dropdown, and then click the green **New repository secret** button.
2. Name the new secret `ACCESS_TOKEN`.
3. Enter the personal access token from the previous step as the value and click **Add secret**.

## Options

| Option              | Description                                                                                                   | Usage Example                        |
|--------------------------|---------------------------------------------------------------------------------------------------------------|--------------------------------------|
| `EXCLUDED`               | Exclude certain repositories by specifying their usernames and repository names as a comma-separated list.  | `someone/repository,another-person/another-repository` |
| `EXCLUDED_LANGS`         | Ignore certain languages by specifying them as a comma-separated list. Languages are not case-sensitive.   | `html,css`                         |
| `EXCLUDE_FORKED_REPOS`   | Show statistics only for "owned" repositories and exclude forks with contributions.                        | `true`                               |
| `EXCLUDE_PRIVATE_REPOS`  | Show statistics for only public repositories and exclude your private ones.                                 | `true`                               |
| `GENERATED_IMAGE_NAME`   | Customize the output path for generated images. Make sure to end with the `.svg` extension and keep the `{{ template }}` and `{{ theme }}` variables somewhere in the name. There are three templates - `overview`, `languages`, `community` - and two themes - `light` and `dark`.                | `{{ template }}-{{ theme }}.svg`                |

To use these options, add a new secret with the specified name and value to your repository's secrets, similar to how you added the access token secret. If you prefer not to use secrets, you can directly set the values in the workflow file by replacing `VARIABLE_NAME: ${{ secrets.VARIABLE_NAME }}` with the desired value (e.g., `VARIABLE_NAME: true`). For options that accept lists of values, provide the values as comma-separated strings within a single string. Make sure not to separate values with spaces though - `apples,oranges` works but `apples, oranges` will not.
