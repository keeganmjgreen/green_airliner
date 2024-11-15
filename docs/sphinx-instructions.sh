# # Installation prerequisites:
# sudo apt install latexmk
# sudo apt install --fix-missing texlive-latex-extra

# Usage:
#     source ~/Dropbox/Documents/Projects/green_airliner/docs/sphinx-instructions.sh
conda activate green_airliner
cd ~/Dropbox/Documents/Projects/green_airliner/
export PYTHONPATH=/home/keegan_green/Dropbox/Documents/Projects/green_airliner/
python src/three_d_sim/config_model.py
generate-schema-doc --config expand_buttons=true --config show_breadcrumbs=false --config  collapse_long_descriptions=false --config with_footer=false \
    configs/simulation_config_json_schema.json docs/source/_static/simulation_config_json_schema.html
rm -r docs/build/html/
cd docs/
make html
# make latexpdf
