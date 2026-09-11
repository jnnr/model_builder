import jinja2
from pathlib import Path
import pandas as pd
import yaml
import shutil
from itertools import chain
from jinja2.meta import find_undeclared_variables
import warnings


class Templater:
    """
    Class to handle templating.

    This class reads a template configuration file, copies necessary data tables,
    and parametrizes templates.

    Attributes
    ----------
    destination : Path
        Destination directory for the generated model files.
    """

    def __init__(self, destination):
        self.templates = {}
        self.data_tables = {}
        self.destination = Path(destination)

    def add_data_table(self, name, **kwargs):
        """Add a data table to the templater."""
        if name in self.data_tables:
            raise ValueError(f"Data table {name} already exists.")
        self.data_tables[name] = kwargs

    def add_template(self, name, **kwargs):
        """Add a template to the templater."""
        if name in self.templates:
            raise ValueError(f"Template {name} already exists.")
        self.templates[name] = kwargs

    def parametrise_templates(self, load_data=None):
        """Parametrise all templates."""
        if load_data is None:
            load_data = lambda path: pd.read_csv(path, index_col=0)

        # first, parametrise model
        model = self._parametrise_model()

        # find all references to templates in the model
        paths_templates = self._collect_paths_templates(model)

        # find all required inputs
        template_base_path = Path(self.templates["model"]["source"]).parent
        required_variables = [
            get_template_variables(template_base_path / path) for path in paths_templates
        ]
        required_variables = list(chain(*required_variables))  # flatten list of lists
        print(f"Required variables: {required_variables}")
        missing_variables = set(required_variables) - set(self.data_tables.keys())
        if missing_variables:
            raise ValueError(f"Missing variables in data tables: {missing_variables}")

        # find all relative paths of data tables
        model_data_tables = model.get("data_tables", {})
        print(f"Model data tables: {model_data_tables.keys()}")
        missing_data_tables = set(model_data_tables.keys()) - set(self.data_tables.keys())
        if missing_data_tables:
            raise ValueError(f"Missing data tables in model: {missing_data_tables}")

        unused_data_tables = set(self.data_tables.keys()) - set(model_data_tables.keys())
        if unused_data_tables:
            warnings.warn(f"Unused data tables will be dropped: {unused_data_tables}")
            for dt in unused_data_tables:
                del self.data_tables[dt]

        for dt in model_data_tables:
            print(model_data_tables[dt])
            self.data_tables[dt]["target"] = model_data_tables[dt]["table"]

        # load required inputs
        data_tables = {}
        for name in required_variables:
            path_data_table = self.data_tables[name]["source"]
            df = load_data(path_data_table)
            data_tables[name] = df

        # parametrize all templates, passing data and template_config
        for path_template in paths_templates:
            print(f"Processing template: {path_template}")
            full_path_template = template_base_path / path_template
            full_path_dest = self.destination / path_template

            parametrise_template(full_path_template, full_path_dest, **data_tables)

    def copy_data_tables(self, copy_func=shutil.copy):
        """Copy all data tables listed in the template configuration to the destination."""
        for _, specs in self.data_tables.items():
            source = Path(specs["source"])
            target = Path(self.destination) / specs["target"]

            if not source.exists():
                raise FileNotFoundError(f"Data table source {source} does not exist.")
            if not target.parent.exists():
                target.parent.mkdir(parents=True)
            if target.exists():
                print(f"Warning: Target {target} already exists and would be overwritten.")
            else:
                print(f"Copying {source} to {target}")
                copy_func(source, target)

    def _parametrise_model(self):
        """Parametrise the model template."""
        path_model_template = self.templates["model"]["source"]
        path_model_target = self.destination / "model.yaml"

        parametrise_template(
            path_model_template,
            path_model_target,
        )
        model = load_yaml(path_model_target)
        return model

    def _collect_paths_templates(self, model):
        """Collect paths of templates from the model configuration."""
        path_templates = []
        path_templates.extend(model["config"]["init"]["math_paths"].values())
        path_templates.extend(model["import"])

        print(f"Paths templates: {path_templates}")
        return path_templates


def load_yaml(path):
    """Load a YAML file."""
    with open(path, "r") as file:
        return yaml.safe_load(file)


def parametrise_template(path_to_template: Path | str, path_to_output_yaml: str | Path, **kwargs):
    """Applies config parameters to template files."""
    path_to_output_yaml = Path(path_to_output_yaml)
    if not path_to_output_yaml.parent.exists():
        path_to_output_yaml.parent.mkdir(parents=True)

    path_to_template = Path(path_to_template)

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(path_to_template.parent),
        lstrip_blocks=True,
        trim_blocks=True,
        keep_trailing_newline=True,
        # The following ensures that missing pandas index elements
        # raise an exception instead of silently returning None
        undefined=jinja2.StrictUndefined,
    )
    # env.filters["unit"] = filters.unit
    rendered = env.get_template(path_to_template.name).render(**kwargs)

    with open(path_to_output_yaml, "w") as result_file:
        result_file.write(rendered)


def copy_data_tables(data_tables, path_data, path_destination):
    """Copies data tables from the template config to the destination."""
    path_destination = Path(path_destination)
    path_data = Path(path_data)
    for table, specs in data_tables.items():
        source = path_data / specs["source"]
        target = path_destination / specs["target"]
        if not source.exists():
            raise FileNotFoundError(f"Data table source {source} does not exist.")
        if not target.parent.exists():
            target.parent.mkdir(parents=True)
        if target.exists():
            print(f"Warning: Target {target} already exists and will be overwritten.")
        else:
            print(f"Copying {source} to {target}")
            shutil.copy(source, target)


def get_template_variables(template_path: Path) -> list[str]:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_path.parent))
    template_source = env.loader.get_source(env, template_path.name)[0]
    parsed_content = env.parse(template_source)
    variables = list(find_undeclared_variables(parsed_content))
    return variables
