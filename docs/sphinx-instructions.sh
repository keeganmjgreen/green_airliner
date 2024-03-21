# # Installation prerequisites:
# sudo apt install latexmk
# sudo apt install --fix-missing texlive-latex-extra

# Usage:
#     source ~/Dropbox/Documents/Projects/electric_airline/docs/sphinx-instructions.sh
conda activate electric_airline
cd ~/Dropbox/Documents/Projects/electric_airline/docs/
make html
make latexpdf
