import os
import toml
import json
import urllib.parse
import urllib.request
import importlib
import sys
import pathlib

from packaging.version import Version, parse as VersionParser


with open('./pyproject.toml') as toml_fh:
	project_info = toml.load(toml_fh)

PROJECT_NAME = project_info['project']['name']
DYNAMIC_VERSION = 'version' in project_info['project'].get('dynamic', [])
VERSION = project_info['project'].get('version')

if DYNAMIC_VERSION:
	if not pathlib.Path(f'./{PROJECT_NAME}/__init__.py').absolute().exists():
		raise KeyError(f"Could not load dynamic version from ./{PROJECT_NAME}/__init__.py'")

	spec = importlib.util.spec_from_file_location(PROJECT_NAME, f'./{PROJECT_NAME}/__init__.py')
	project = importlib.util.module_from_spec(spec)
	sys.modules[PROJECT_NAME] = project
	spec.loader.exec_module(sys.modules[PROJECT_NAME])
	VERSION = sys.modules[PROJECT_NAME].__version__

def get_upstream_version():
	if homepage := project_info['project'].get('homepage'):
		meta = urllib.parse.urlparse(homepage)
		_, owner, *_ = meta.path.split('/')
		
		endpoint = f"https://api.github.com/repos/{owner}/{PROJECT_NAME}/releases"

		response = urllib.request.urlopen(endpoint, timeout=5)
		data = response.read()

		release_history = json.loads(data.decode())
		versions = []
		higest_version = None

		for version in release_history:
			version_number = version['name']

			if version_number[0] == 'v':
				version_number = version_number[1:]

			version_obj = VersionParser(version_number)
			versions.append(version_obj)

			if higest_version is None or version_obj > higest_version:
				higest_version = version_obj
		
		return {
			'latest' : higest_version,
			'versions' : versions
		}

version_history = get_upstream_version()
if VERSION[0] == 'v':
	VERSION = VERSION[1:]
VERSION = VersionParser(VERSION)
if VERSION == version_history['latest']:
	print('Collision with latest version')
	exit(1)
elif VERSION in version_history['versions']:
	print('Collision with previous versions')
	exit(1)

os.system(f'git tag -s v{str(VERSION)} -m \'v{str(VERSION)}\'')
os.system(f'git push origin --tags')
os.system(f'git archive --format=tar.gz --prefix=junk/ HEAD > {PROJECT_NAME}-{str(VERSION)}.tar.gz')
os.system(f'gpg --output {PROJECT_NAME}-{str(VERSION)}.tar.gz.sig --detach-sig {PROJECT_NAME}-{str(VERSION)}.tar.gz')
