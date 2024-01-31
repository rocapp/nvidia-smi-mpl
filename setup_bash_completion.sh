#!/bin/bash

chmod +x ./.bash_completion/nvidia-smi-mpl.bash-completion

mkdir -p ~/.bash_completion

cp ./.bash_completion/nvidia-smi-mpl.bash-completion ~/.bash_completion/nvidia-smi-mpl.bash-completion


if grep -q "# Bash completion for nvidia-smi-mpl:" ~/.bashrc && grep -q "source ~/.bash_completion/nvidia-smi-mpl.bash-completion" ~/.bashrc; then
    echo -e "\nBash completion for nvidia-smi-mpl already exists in ~/.bashrc, skipping..."
    exit 0
else
    echo -e "\nAdding bash completion for nvidia-smi-mpl to ~/.bashrc"
    echo -e "\n# Bash completion for nvidia-smi-mpl:" >> ~/.bashrc
    echo -e "source ~/.bash_completion/nvidia-smi-mpl.bash-completion\n" >> ~/.bashrc
fi

echo -e "\nSuccessfully installed bash completion for nvidia-smi-mpl"
echo -e "Please restart your terminal or run the following command:\n"
echo -e "\t'source ~/.bashrc'\n"