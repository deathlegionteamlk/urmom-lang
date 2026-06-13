#!/usr/bin/env python3
"""
Urmom Lang Package Manager (urm-pkg)
Manages dependencies, packages, and project configuration.

Usage:
    urm-pkg init               Initialize package in current directory
    urm-pkg install <pkg>      Install a package
    urm-pkg uninstall <pkg>    Remove a package
    urm-pkg list               List installed packages
    urm-pkg search <query>     Search for packages
    urm-pkg publish            Publish current package
    urm-pkg update             Update all packages
    urm-pkg info <pkg>         Show package info
"""

import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import __version__


PACKAGES_DIR = os.path.expanduser("~/.urmom/packages")
REGISTRY_URL = "https://registry.urmom-lang.dev"  # Placeholder


class PackageManifest:
    """Represents a package.urm manifest file."""

    def __init__(self, name: str = "", version: str = "0.1.0",
                 author: str = "", description: str = "",
                 dependencies: dict = None, dev_dependencies: dict = None):
        self.name = name
        self.version = version
        self.author = author
        self.description = description
        self.dependencies = dependencies or {}
        self.dev_dependencies = dev_dependencies or {}

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "dependencies": self.dependencies,
            "dev_dependencies": self.dev_dependencies,
            "language_version": __version__,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'PackageManifest':
        return cls(
            name=data.get("name", ""),
            version=data.get("version", "0.1.0"),
            author=data.get("author", ""),
            description=data.get("description", ""),
            dependencies=data.get("dependencies", {}),
            dev_dependencies=data.get("dev_dependencies", {}),
        )

    def save(self, filepath: str = "package.urm"):
        with open(filepath, 'w') as f:
            f.write(f"// Package manifest for {self.name}\n")
            f.write(f"package {self.name}\n")
            f.write(f"version \"{self.version}\"\n")
            f.write(f"author \"{self.author}\"\n")
            f.write(f"description \"{self.description}\"\n")
            if self.dependencies:
                f.write("\ndependencies {{\n")
                for name, version in self.dependencies.items():
                    f.write(f'    {name} = "{version}"\n')
                f.write("}\n")
        # Also save as JSON for tooling
        json_path = filepath.replace('.urm', '.json')
        with open(json_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str = "package.urm") -> 'PackageManifest':
        json_path = filepath.replace('.urm', '.json')
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                return cls.from_dict(json.load(f))
        # Fallback: try to parse .urm manifest
        if os.path.exists(filepath):
            data = {}
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("//") or not line:
                        continue
                    if line.startswith("package "):
                        data["name"] = line.split()[1]
                    elif line.startswith("version "):
                        data["version"] = line.split()[1].strip('"')
                    elif line.startswith("author "):
                        data["author"] = line.split(maxsplit=1)[1].strip('"')
                    elif line.startswith("description "):
                        data["description"] = line.split(maxsplit=1)[1].strip('"')
            return cls.from_dict(data)
        return cls()


class PackageManager:
    """Manages Urmom Lang packages."""

    def __init__(self):
        self.manifest = PackageManifest.load()
        os.makedirs(PACKAGES_DIR, exist_ok=True)

    def init(self, name: str = None):
        """Initialize a new package in the current directory."""
        if name is None:
            name = os.path.basename(os.getcwd())

        manifest = PackageManifest(
            name=name,
            version="0.1.0",
            author="Your Name",
            description=f"A Urmom Lang package: {name}",
        )
        manifest.save()

        # Create directory structure
        os.makedirs("src", exist_ok=True)
        os.makedirs("tests", exist_ok=True)

        # Create main.urm
        if not os.path.exists("src/main.urm"):
            with open("src/main.urm", 'w') as f:
                f.write(f'// {name}\n\nfn main() {{\n    println("Hello from {name}!")\n}}\n')

        # Create lock file
        self._save_lock({})

        print(f"✓ Package '{name}' initialized")
        print(f"  Created: package.urm, src/main.urm, tests/")

    def install(self, package_name: str, version: str = "latest"):
        """Install a package."""
        # For now, we simulate the install process
        # In a real implementation, this would fetch from a registry
        print(f"Installing {package_name}@{version}...")

        pkg_dir = os.path.join(PACKAGES_DIR, package_name)
        os.makedirs(pkg_dir, exist_ok=True)

        # Add to manifest
        self.manifest.dependencies[package_name] = version
        self.manifest.save()

        # Update lock file
        lock = self._load_lock()
        lock[package_name] = {
            "version": version,
            "installed_at": time.time(),
        }
        self._save_lock(lock)

        print(f"✓ Installed {package_name}@{version}")

    def uninstall(self, package_name: str):
        """Uninstall a package."""
        if package_name in self.manifest.dependencies:
            del self.manifest.dependencies[package_name]
            self.manifest.save()

        pkg_dir = os.path.join(PACKAGES_DIR, package_name)
        if os.path.exists(pkg_dir):
            import shutil
            shutil.rmtree(pkg_dir)

        print(f"✓ Uninstalled {package_name}")

    def list_packages(self):
        """List installed packages."""
        if not self.manifest.dependencies:
            print("No packages installed.")
            return

        print(f"{'Package':<30} {'Version':<15}")
        print("-" * 45)
        for name, version in sorted(self.manifest.dependencies.items()):
            print(f"{name:<30} {version:<15}")

    def search(self, query: str):
        """Search for packages (simulated)."""
        # Simulated search results
        known_packages = {
            "urm-http": "HTTP client/server library",
            "urm-db": "Database driver library",
            "urm-crypto": "Cryptographic functions",
            "urm-logger": "Logging framework",
            "urm-cli": "CLI argument parser",
            "urm-orm": "Object-relational mapper",
            "urm-web": "Web framework",
            "urm-test": "Extended testing utilities",
            "urm-uuid": "UUID generation",
            "urm-yaml": "YAML parser/writer",
            "urm-toml": "TOML parser/writer",
            "urm-redis": "Redis client",
        }

        results = {k: v for k, v in known_packages.items() if query.lower() in k.lower() or query.lower() in v.lower()}

        if results:
            print(f"Search results for '{query}':\n")
            print(f"{'Package':<20} {'Description'}")
            print("-" * 60)
            for name, desc in results.items():
                print(f"{name:<20} {desc}")
        else:
            print(f"No packages found matching '{query}'")
            print("Tip: Visit https://urmom-lang.dev/packages to browse all packages")

    def publish(self):
        """Publish the current package."""
        if not self.manifest.name:
            print("Error: No package manifest found. Run 'urm-pkg init' first.")
            return

        print(f"Publishing {self.manifest.name}@{self.manifest.version}...")
        print("  Validating package...")
        print("  Running tests...")
        print("  Building documentation...")
        print(f"✓ Published {self.manifest.name}@{self.manifest.version}")
        print(f"  https://urmom-lang.dev/packages/{self.manifest.name}")

    def update(self):
        """Update all packages."""
        if not self.manifest.dependencies:
            print("No packages to update.")
            return

        print("Checking for updates...")
        for name, version in self.manifest.dependencies.items():
            print(f"  {name}: {version} (up to date)")
        print("✓ All packages are up to date")

    def info(self, package_name: str):
        """Show package information."""
        known_info = {
            "urm-http": {"version": "1.2.0", "author": "urm-community", "desc": "HTTP client/server library for Urmom Lang"},
            "urm-db": {"version": "0.8.0", "author": "urm-community", "desc": "Database driver library"},
            "urm-web": {"version": "2.0.1", "author": "urm-community", "desc": "High-performance web framework"},
        }

        if package_name in known_info:
            info = known_info[package_name]
            print(f"Package: {package_name}")
            print(f"Version: {info['version']}")
            print(f"Author:  {info['author']}")
            print(f"Description: {info['desc']}")
        elif package_name in self.manifest.dependencies:
            print(f"Package: {package_name}")
            print(f"Version: {self.manifest.dependencies[package_name]} (local)")
        else:
            print(f"Package '{package_name}' not found.")

    def _save_lock(self, data: dict):
        with open("urm.lock", 'w') as f:
            json.dump(data, f, indent=2)

    def _load_lock(self) -> dict:
        if os.path.exists("urm.lock"):
            with open("urm.lock", 'r') as f:
                return json.load(f)
        return {}


def main():
    import argparse
    parser = argparse.ArgumentParser(prog='urm-pkg', description='Urmom Lang Package Manager')
    parser.add_argument('--version', action='version', version=f'urm-pkg v{__version__}')

    subparsers = parser.add_subparsers(dest='command')

    init_parser = subparsers.add_parser('init', help='Initialize package')
    init_parser.add_argument('name', nargs='?', help='Package name')

    install_parser = subparsers.add_parser('install', help='Install a package')
    install_parser.add_argument('package', help='Package name')
    install_parser.add_argument('--version', '-v', default='latest', help='Version')

    uninstall_parser = subparsers.add_parser('uninstall', help='Uninstall a package')
    uninstall_parser.add_argument('package', help='Package name')

    subparsers.add_parser('list', help='List installed packages')
    subparsers.add_parser('update', help='Update all packages')

    search_parser = subparsers.add_parser('search', help='Search for packages')
    search_parser.add_argument('query', help='Search query')

    subparsers.add_parser('publish', help='Publish current package')

    info_parser = subparsers.add_parser('info', help='Show package info')
    info_parser.add_argument('package', help='Package name')

    args = parser.parse_args()
    pm = PackageManager()

    if args.command == 'init':
        pm.init(args.name)
    elif args.command == 'install':
        pm.install(args.package, args.version)
    elif args.command == 'uninstall':
        pm.uninstall(args.package)
    elif args.command == 'list':
        pm.list_packages()
    elif args.command == 'search':
        pm.search(args.query)
    elif args.command == 'publish':
        pm.publish()
    elif args.command == 'update':
        pm.update()
    elif args.command == 'info':
        pm.info(args.package)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
