import importlib.util
import os
import sys
import sysconfig


def _load_stdlib(name):
    stdlib_path = sysconfig.get_paths()["stdlib"]
    package_dir = os.path.join(stdlib_path, name)
    module_path = os.path.join(package_dir, "__init__.py")
    spec = importlib.util.spec_from_file_location(f"_stdlib_{name}", module_path, submodule_search_locations=[package_dir])
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"_stdlib_{name}"] = module
    spec.loader.exec_module(module)
    return module


_stdlib_logging = _load_stdlib("logging")

basicConfig = _stdlib_logging.basicConfig
getLogger = _stdlib_logging.getLogger
INFO = _stdlib_logging.INFO
WARNING = _stdlib_logging.WARNING
ERROR = _stdlib_logging.ERROR

__all__ = ["basicConfig", "getLogger", "INFO", "WARNING", "ERROR"]
