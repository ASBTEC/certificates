#!/usr/bin/env bash

main()
{
  INPUT_FILE="${PROJECT_FOLDER}/in/data.csv"
  OUTPUT_FOLDER="${PROJECT_FOLDER}/data"

  # Ensure the output folder exists
  mkdir -p "$OUTPUT_FOLDER"

  # Initialize a counter for file numbering
  counter=1

  # Read the CSV file line by line
  while IFS=',' read -r NAME DNI EMAIL; do
    EMAIL=$(echo "$EMAIL" | tr -d '\n' | tr -d '\r')
    # Build the JSON content for each line
    JSON_CONTENT=$(cat <<EOF
{
  "name": "${NAME}",
  "email": "${EMAIL}",
  "dni": "${DNI}"
}
EOF
    )

    # Save the JSON content to a file with a correlative number
    echo "$JSON_CONTENT" > "${OUTPUT_FOLDER}/${EMAIL/@/_at_}.json"
  done < "$INPUT_FILE"

  echo "JSON files generated successfully in $OUTPUT_FOLDER."
}

PROJECT_FOLDER="$(cd "$(dirname "$(realpath "$0")")/../" &>/dev/null && pwd)"
main "$@"