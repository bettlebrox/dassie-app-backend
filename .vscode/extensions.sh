#!/bin/bash

# Read extensions from .vscode/extensions.json and install them
extensions=$(cat .vscode/extensions.json | jq -r '.recommendations[]')
for extension in $extensions; do
    cursor --install-extension $extension
done
