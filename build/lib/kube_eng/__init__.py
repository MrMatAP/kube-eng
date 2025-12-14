import pathlib
import importlib.metadata

try:
    __version__ = importlib.metadata.version('kube-eng')
except importlib.metadata.PackageNotFoundError:
    # You have not yet installed this as a package, likely because you're hacking on it in some IDE
    __version__ = '0.0.0.dev0'

__default_config_path__ = pathlib.Path.home() / '.kube-eng'
__ansible_project_dir__ = pathlib.Path(__file__).parent / 'ansible'