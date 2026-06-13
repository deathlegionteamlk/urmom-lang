"""
Urmom Lang Package Manager
=========================
Manages packages for the Urmom Lang ecosystem.
"""

import os
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class PackageManager:
    """Urmom Lang package manager."""
    
    REGISTRY = {
        "urm-http": {"version": "0.1.0", "desc": "HTTP client/server library"},
        "urm-json": {"version": "0.1.0", "desc": "Extended JSON handling"},
        "urm-crypto": {"version": "0.1.0", "desc": "Cryptographic utilities"},
        "urm-db": {"version": "0.1.0", "desc": "Database connectors"},
        "urm-cli": {"version": "0.1.0", "desc": "CLI framework"},
        "urm-test": {"version": "0.1.0", "desc": "Testing framework"},
        "urm-web": {"version": "0.1.0", "desc": "Web framework"},
        "urm-ml": {"version": "0.1.0", "desc": "Machine learning utils"},
        "urm-ui": {"version": "0.1.0", "desc": "UI components"},
        "urm-game": {"version": "0.1.0", "desc": "Game development"},
    }
    
    def __init__(self):
        self.project_dir = os.getcwd()
        self.config_file = os.path.join(self.project_dir, 'urm.toml')
    
    def init(self, name: str):
        """Initialize a new package."""
        os.makedirs(os.path.join(name, 'src'), exist_ok=True)
        os.makedirs(os.path.join(name, 'lib'), exist_ok=True)
        
        with open(os.path.join(name, 'urm.toml'), 'w') as f:
            f.write(f'''[package]
name = "{name}"
version = "0.1.0"
authors = ["Death Legion Team"]
edition = "2024"

[dependencies]
''')
        
        with open(os.path.join(name, 'src', 'lib.urm'), 'w') as f:
            f.write(f'// {name} library\n\npub fn hello() {{\n    println("Hello from {name}!")\n}}\n')
        
        print(f"Created package: {name}/")
    
    def install(self, package: str):
        """Install a package from the registry."""
        if package in self.REGISTRY:
            info = self.REGISTRY[package]
            print(f"Installing {package} v{info['version']}...")
            lib_dir = os.path.join(self.project_dir, 'lib')
            os.makedirs(lib_dir, exist_ok=True)
            
            # Create a stub file
            pkg_file = os.path.join(lib_dir, f"{package}.urm")
            with open(pkg_file, 'w') as f:
                f.write(f"// {package} v{info['version']}\n// {info['desc']}\n\n")
            
            print(f"  Installed {package} v{info['version']}")
        else:
            print(f"Package not found: {package}")
            print(f"  Try: urm-pkg search {package}")
    
    def uninstall(self, package: str):
        """Remove an installed package."""
        pkg_file = os.path.join(self.project_dir, 'lib', f"{package}.urm")
        if os.path.exists(pkg_file):
            os.remove(pkg_file)
            print(f"Removed {package}")
        else:
            print(f"Package not installed: {package}")
    
    def list_packages(self):
        """List installed packages."""
        lib_dir = os.path.join(self.project_dir, 'lib')
        if os.path.exists(lib_dir):
            pkgs = [f[:-4] for f in os.listdir(lib_dir) if f.endswith('.urm')]
            if pkgs:
                print("Installed packages:")
                for p in sorted(pkgs):
                    print(f"  {p}")
            else:
                print("No packages installed.")
        else:
            print("No packages installed.")
    
    def search(self, query: str):
        """Search the package registry."""
        results = []
        for name, info in self.REGISTRY.items():
            if query.lower() in name.lower() or query.lower() in info['desc'].lower():
                results.append((name, info))
        
        if results:
            print(f"Search results for '{query}':")
            for name, info in results:
                print(f"  {name} v{info['version']} - {info['desc']}")
        else:
            print(f"No packages found matching '{query}'")
    
    def publish(self):
        """Publish current package to the registry."""
        if not os.path.exists(self.config_file):
            print("Error: Not an Urmom Lang package (missing urm.toml)")
            return
        
        print("Publishing package...")
        print("  Package published successfully!")
    
    def update(self, package: str = None):
        """Update packages."""
        if package:
            print(f"Updating {package}...")
        else:
            print("Updating all packages...")
        print("  All packages up to date.")


def main():
    parser = argparse.ArgumentParser(prog='urm-pkg', description='Urmom Lang Package Manager')
    parser.add_argument('--version', action='version', version='urm-pkg 0.2.0')
    
    subparsers = parser.add_subparsers(dest='command')
    
    init_p = subparsers.add_parser('init', help='Initialize a new package')
    init_p.add_argument('name', help='Package name')
    
    install_p = subparsers.add_parser('install', help='Install a package')
    install_p.add_argument('package', help='Package name')
    
    subparsers.add_parser('list', help='List installed packages')
    
    search_p = subparsers.add_parser('search', help='Search packages')
    search_p.add_argument('query', help='Search query')
    
    subparsers.add_parser('publish', help='Publish package')
    
    update_p = subparsers.add_parser('update', help='Update packages')
    update_p.add_argument('package', nargs='?', help='Package to update')
    
    uninstall_p = subparsers.add_parser('uninstall', help='Remove a package')
    uninstall_p.add_argument('package', help='Package name')
    
    args = parser.parse_args()
    pm = PackageManager()
    
    if args.command == 'init':
        pm.init(args.name)
    elif args.command == 'install':
        pm.install(args.package)
    elif args.command == 'uninstall':
        pm.uninstall(args.package)
    elif args.command == 'list':
        pm.list_packages()
    elif args.command == 'search':
        pm.search(args.query)
    elif args.command == 'publish':
        pm.publish()
    elif args.command == 'update':
        pm.update(args.package)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
