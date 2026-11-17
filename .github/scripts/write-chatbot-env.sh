#!/usr/bin/env bash
# Writes the AI Chatbot service PROD .env from Secrets Manager to chatbot-service/.env, as the legacy Jenkins job
# chatbot-service does (stage "Startup": the whole SecretString of the legacy secret to chatbot-service/.env, then
# `sed -i "s/\r//g" .env`, before `docker build .`). The secret id is the legacy one, unchanged (CICD_ENV_SECRET_ID of
# the chatbot-prod environment). The original Dockerfile copies the file into the image (COPY .env ./), as today.
#
# The value goes from the AWS CLI straight to the file: it is never echoed and never a step or job output; only its
# values are read back to register log masks. The workflow removes it with remove-chatbot-env.sh in an `if: always()`
# step. Code adapted from write-sync-env.sh (onecgiar_result_functions); differences: the path, the legacy CR removal
# and the final file mode (see below).
# Inputs (environment): SECRET_ID, AWS_REGION and the step-scoped temporary credentials.
set -euo pipefail
: "${SECRET_ID:?}" "${AWS_REGION:?}"

file="chatbot-service/.env"

# Refuse to write anywhere git would track: the file must stay ignored.
git check-ignore -q "$file" \
  || { echo "::error::$file is not git-ignored (fail closed)"; exit 1; }

umask 077
if ! aws secretsmanager get-secret-value --region "$AWS_REGION" --secret-id "$SECRET_ID" \
       --query SecretString --output text > "$file" 2> /dev/null; then
  rm -f "$file"
  # The CLI error is not printed: it may quote request details. The id is a masked environment secret.
  echo "::error::could not read the chatbot secret (check the build role and the secret id)"
  exit 1
fi
if [ ! -s "$file" ]; then
  rm -f "$file"
  echo "::error::the chatbot secret is empty (fail closed)"
  exit 1
fi

# Legacy line: sed -i "s/\r//g" .env
sed -i "s/\r//g" "$file"

# Defense in depth only (the protection is that nothing prints the file): register every value of 8+ characters as a
# log mask, so an accidental echo in a later step of this job shows `***`. Comments and blank lines are skipped; the
# key ends at the first `=` or `:`. Workflow commands are consumed by the runner and never shown.
masked=0
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in '' | '#'*) continue ;; esac
  [[ "$line" =~ ^[^=:]*[=:][[:space:]]*(.*)$ ]] || continue
  value="${BASH_REMATCH[1]}"
  value="${value//'%'/'%25'}"
  [ "${#value}" -ge 8 ] || continue
  echo "::add-mask::${value}"
  masked=$((masked + 1))
done < "$file"

# COPY keeps the file mode in the image, and the Lambda runtime does not run as root: the legacy file had the default
# mode 0644 (umask 022 on the Jenkins agent). Same mode here, set only after the file is complete; the runner is
# ephemeral and the file is removed after the build.
chmod 0644 "$file"

echo "Chatbot .env written (1 file, mode 0644 as the legacy job, ${masked} values masked)"
