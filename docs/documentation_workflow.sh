# Read the `.env` file (specifically for the `PYTHONPATH` specified therein):
set -o allexport && source .env && set +o allexport

# Activate the Conda environment:
conda activate green_airliner

# Run `simulation_config_schema.py`, whose main guard will convert the `SimulationConfig` Pydantic
#     model therein to JSON Schema `simulation_config_json_schema.json`.
python src/three_d_sim/simulation_config_schema.py

# Convert the JSON Schema to an interactive HTML page:
generate-schema-doc \
    --config expand_buttons=true \
    --config show_breadcrumbs=false \
    --config collapse_long_descriptions=false \
    --config with_footer=false \
    src/three_d_sim/simulation_config_json_schema.json \
    docs/_static/simulation_config_json_schema.html

cd docs/

# Clear any HTML or LaTeX documentation that have already been built (else do nothing):
rm -r build/html/ || :
rm -r build/latex/ || :

make html
# make latexpdf

# Return to the repo root for any further runs:
cd ../
