# # Installation prerequisites:
# sudo apt install latexmk
# sudo apt install --fix-missing texlive-latex-extra

# Usage:
#     source ~/Dropbox/Documents/Projects/electric_airline/docs/sphinx-instructions.sh
conda activate electric_airline

cd ~/Dropbox/Documents/Projects/electric_airline/docs/

python ../src/three_d_sim/config_model.py
rm -r build/html/
generate-schema-doc ../configs/simulation_config_json_schema.json source/_static/simulation_config_json_schema.html

make html
# make latexpdf
