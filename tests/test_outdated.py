# %%
from dataclasses import dataclass
from pathlib import Path
import sys
import yaml

import packaging.version
import requests

recipes_dir = Path(__file__).parents[1] / 'recipes'
recipies = sorted([
    str(recipe) for recipe in recipes_dir.iterdir()
    if recipe.is_dir()
])
latest_recipe_dir = Path(recipies[-1])
construct_yaml_path = latest_recipe_dir / 'construct.yaml'

construct_yaml = yaml.safe_load(
    construct_yaml_path.read_text(encoding='utf-8')
)
specs = construct_yaml['specs']

print(f'Analyzing spec file: {construct_yaml_path}\n')

@dataclass()
class Package:
    name: str
    version_spec: str | None
    version_conda_forge: str | None = None

packages: list[Package] = []

for spec in specs:
    if ' ' in spec:
        assert spec.count(' ') == 1, f'Wrong number of spaces in spec: {spec}'
        name, version = spec.split(' ')
        version = (
            version
            .lstrip('~')
            .lstrip('=')
            .split('=')  # build number
        )[0]
    else:
        name = spec
        version = None

    packages.append(
        Package(name=name, version_spec=version)
    )
    del name, version

outdated = []
not_found = []
for package in packages:
    if package.version_spec is None:
        continue

    anaconda_url = f'https://api.anaconda.org/package/conda-forge/{package.name}'
    r =  requests.get(anaconda_url)
    if r.status_code == 404:
        print(f'{package.name} not found on conda-forge')
        not_found.append(package)
        continue

    json = r.json()
    version = json['latest_version']
    package.version_conda_forge = version
    del json, version

    if (
        packaging.version.parse(package.version_spec) <
        packaging.version.parse(package.version_conda_forge)
    ):
        print(f'* {package.name.ljust(20)} OUTDATED')
        outdated.append(package)
    else:
        print(f'  {package.name.ljust(20)} up to date')

exit_code = 0
if not_found:
    print(f'\n{len(not_found)} packages not found on conda-forge:\n')
    print('\n'.join(f' * {package.name}' for package in not_found))
    exit_code = 1

if outdated:
    print(f'\n{len(outdated)} packages outdated:\n')
    print('\n'.join([
        f' * {package.name} '
        f'({package.version_spec} < {package.version_conda_forge})'
        for package in outdated
    ]))
    exit_code = 1
else:
    print('\nEverything is up to date.')
if __name__ == '__main__':
    sys.exit(exit_code)
