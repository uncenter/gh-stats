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
4. Set your preferred 'Expiration' date (no expiration if you want to just "set and forget").
5. Select `repo` for full control of private repositories.
6. Select `read:user` for read-only access to all user profile data.
7. Click the 'Generate token' button.
8. Copy the generated token - this is the one and only time to copy it.

You'll then need to create a new repository secret for this token:

1. Go to the **Settings** tab of the repository, click the **Secrets and variables** item on the side panel, click **Actions** in the expanded dropdown, and then click the green **New repository secret** button.
2. Name the new secret `ACCESS_TOKEN`.
3. Enter the personal access token from the previous step as the value and click **Add secret**.

## Options

For each of the following options, add a new secret with the name and value to your repository's secrets like you did for the access token. Some of the values are added as secrets by default to prevent leaking information about private repositories. If you're not worried about that, you can change the values directly in the workflow itself - just replace `VARIABLE_NAME: ${{ secrets.VARIABLE_NAME }}` with the value you want, like `VARIABLE_NAME: true`. Any options which take "lists" of values should be set as comma seperated values inside a single string.

- To exclude certain repositories, set the variable `EXCLUDED` to `USERNAME/REPOSITORY,USERNAME/REPOSITORY2`.
- To ignore certain languages, set the variable `EXCLUDED_LANGS` to `lang,lang2`. Languages are not case sensitive.
- To show statistics only for "owned" repositories and not forks with contributions, set the variable called `EXCLUDE_FORKED_REPOS` to `true`.
- To show statistics for only public repositories and not your privated ones, set the variable `EXCLUDE_PRIVATE_REPOS` to `true`.
- To customize the output path, set the `GENERATED_IMAGE_NAME` variable. The default is `{{ template }}-{{ theme }}.svg`, which will generate files like `overview-dark.svg` and `languages-light.svg`. Make sure to include the `.svg` extension and keep the `{{ template }}` and `{{ theme }}` variables (somewhere) in the name.
