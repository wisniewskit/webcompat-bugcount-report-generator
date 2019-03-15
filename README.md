### Installing dependencies
This script assumes you can run Python 3.6, and have [`pipenv`](https://pipenv.readthedocs.io/en/latest/) installed.

Once that's true, run:

```
pipenv install
```

### Environment variables

The script also assumes an environment variable `GITHUB_API_TOKEN` is set to a [personal access token](https://help.github.com/en/articles/creating-a-personal-access-token-for-the-command-line). Alternately, you can create a `.env` file in the project root that looks like:

```
GITHUB_API_TOKEN=tokenvaluehere
```

### Running the scraper

```
pipenv run scrape
```

After it's done, there will be a fresh new .csv file in `./data/export`.

