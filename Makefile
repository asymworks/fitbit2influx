export FLASK_APP := fitbit2influx.factory

shell serve db-init db-migrate db-upgrade db-downgrade : export FLASK_ENV := development
coverage coverage-html coverage-report test test-wip test-x : export FLASK_ENV := production

shell-psql serve-psql export : export FLASK_ENV := development
shell-psql serve-psql export : export JADETREE_CONFIG := ../config/dev-docker.py

coverage :
	poetry run coverage run --source=jadetree -m pytest tests

coverage-html :
	poetry run coverage html -d .htmlcov && open .htmlcov/index.html

coverage-report :
	poetry run coverage report -m

db-init :
	poetry run flask db init

db-migrate :
	poetry run flask db migrate

db-upgrade :
	poetry run flask db upgrade

db-downgrade :
	poetry run flask db downgrade

lint :
	poetry run flake8

requirements.txt : poetry.lock
	poetry export -f requirements.txt --without-hashes -o requirements.txt

requirements-dev.txt : poetry.lock
	poetry export --dev -f requirements.txt --without-hashes -o requirements-dev.txt

shell :
	poetry run flask shell

serve :
	poetry run flask run

test :
	poetry run python -m pytest tests

test-x :
	poetry run python -m pytest tests -x

test-wip :
	poetry run python -m pytest tests -m wip

all: serve

.PHONY: coverage coverage-html coverage-report \
	db-init db-migrate db-upgrade db-downgrade \
	lint shell serve test test-wip test-x