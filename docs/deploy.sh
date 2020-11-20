#!/usr/bin/env sh

set -e

npm run build

cd .vuepress/dist

git init
git add -A
git commit -m 'deploy'

git push -f git@github.com:wh1te909/tacticalrmm.git develop:gh-pages
cd -