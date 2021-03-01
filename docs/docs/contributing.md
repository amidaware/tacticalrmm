# Contributing

### Contributing to the docs

Docs are built with [MKDocs for Material](https://squidfunk.github.io/mkdocs-material/)

To setup a local environment to add/edit to this documentation site:

```bash
mkdir ~/rmmdocs && cd ~/rmmdocs
git clone https://github.com/wh1te909/tacticalrmm.git .
python3 -m venv env
source env/bin/activate
pip install --upgrade pip
pip install --upgrade setuptools wheel
pip install -r api/tacticalrmm/requirements-dev.txt
cd docs
mkdocs serve
```

Open your browser and navigate to `http://yourserverip:8005`

Add/edit markdown files in the `docs/docs` folder and you'll see live changes at the url above.

Edit `docs/mkdocs.yml` to edit structure and add new files.

Full mkdocs documentation [here](https://squidfunk.github.io/mkdocs-material/getting-started/)

Once finished, [create a pull request](https://www.digitalocean.com/community/tutorials/how-to-create-a-pull-request-on-github) to the `develop` branch for review.
