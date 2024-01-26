dir=$(dirname "$BASH_SOURCE")

# 1. Set per-user env vars from .env
dot_env_file="${dir}/.env"

if [[ -f "${dot_env_file}" ]]; then
    # Remove CR and LF
    for env_var in $(grep -v '^#' "${dot_env_file}" | tr -d '\r' | xargs -d '\n'); do
        for kv in "${env_var[@]}"; do
            IFS='=' read -r k v <<<"$kv"
            export $k=$v
            if [[ "$RENDER_SUMMARY" = true ]]; then
                env_var_origin_map["${k}"]="${dot_env_file}"
                env_var_value_map["${k}"]="${v}"
            fi
        done
    done
fi
