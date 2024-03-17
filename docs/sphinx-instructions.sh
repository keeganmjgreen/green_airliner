# Installation prerequisites:
sudo apt install latexmk
sudo apt install --fix-missing texlive-latex-extra

# Usage:
conda activate electric-airline
cd ../electric_airline/docs/
make html
make latexpdf
