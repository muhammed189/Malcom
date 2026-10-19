import importlib.util
import os
import sys
import sysconfig


def _load_stdlib(name):
    stdlib_path = sysconfig.get_paths()["stdlib"]
    module_path = os.path.join(stdlib_path, name + ".py")
    package_dir = None
    if name in {"json", "logging"}:
        package_dir = os.path.join(stdlib_path, name)
        module_path = os.path.join(package_dir, "__init__.py")
    spec = importlib.util.spec_from_file_location(f"_stdlib_{name}", module_path, submodule_search_locations=[package_dir] if package_dir else None)
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"_stdlib_{name}"] = module
    spec.loader.exec_module(module)
    return module


_stdlib_json = _load_stdlib("json")

dumps = _stdlib_json.dumps
loads = _stdlib_json.loads
dump = _stdlib_json.dump
load = _stdlib_json.load
JSONDecodeError = _stdlib_json.JSONDecodeError

__all__ = ["dumps", "loads", "dump", "load", "JSONDecodeError"]
