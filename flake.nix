{
  description = "Deluge TemporaryPause plugin";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      system = "aarch64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      python = pkgs.python3;

      # Build the .egg file that Deluge loads from its plugins directory
      egg = pkgs.stdenv.mkDerivation {
        pname = "deluge-temporarypause";
        version = "0.1";
        src = ./.;
        nativeBuildInputs = [ python python.pkgs.setuptools ];
        buildPhase = ''
          ${python}/bin/python setup.py bdist_egg
        '';
        installPhase = ''
          mkdir -p $out
          cp dist/*.egg $out/
        '';
      };

      # Script that builds and installs the egg into ~/.config/deluge/plugins/
      installScript = pkgs.writeShellApplication {
        name = "install-temporarypause";
        runtimeInputs = [ python python.pkgs.setuptools ];
        text = ''
          set -e
          PLUGIN_DIR="''${XDG_CONFIG_HOME:-$HOME/.config}/deluge/plugins"
          mkdir -p "$PLUGIN_DIR"
          python setup.py bdist_egg
          cp dist/*.egg "$PLUGIN_DIR/"
          echo "Installed to $PLUGIN_DIR"
          echo "Enable the plugin in Deluge Preferences > Plugins > TemporaryPause"
        '';
      };
    in
    {
      packages.${system} = {
        default = egg;
        install = installScript;
      };

      # nix run .#install  — build and drop the egg into ~/.config/deluge/plugins/
      apps.${system}.install = {
        type = "app";
        program = "${installScript}/bin/install-temporarypause";
      };

      devShells.${system}.default = pkgs.mkShell {
        packages = [
          python
          python.pkgs.setuptools
          python.pkgs.twisted
        ];
        shellHook = ''
          echo "Run 'python setup.py bdist_egg' to build the plugin egg"
          echo "Then copy dist/*.egg to ~/.config/deluge/plugins/"
        '';
      };
    };
}
