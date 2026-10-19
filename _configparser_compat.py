import importlib.util
import os
import sysconfig


def _load_stdlib(name):
    stdlib_path = sysconfig.get_paths()["stdlib"]
    module_path = os.path.join(stdlib_path, name + ".py")
    if not os.path.exists(module_path):
        if name == "json":
            module_path = os.path.join(stdlib_path, "json", "__init__.py")
        elif name == "configparser":
            module_path = os.path.join(stdlib_path, "configparser.py")
        elif name == "logging":
            module_path = os.path.join(stdlib_path, "logging", "__init__.py")
    spec = importlib.util.spec_from_file_location(f"_stdlib_{name}", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_stdlib_configparser = _load_stdlib("configparser")
ConfigParser = _stdlib_configparser.ConfigParser
Error = _stdlib_configparser.Error

__all__ = ["ConfigParser", "Error"]
