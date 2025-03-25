#!/usr/bin/env bash

PROJECT_FOLDER="$(cd "$(dirname "$(realpath "$0")")/../" &>/dev/null && pwd)"

rm -rf "${PROJECT_FOLDER}"/certs/*.html
rm -rf "${PROJECT_FOLDER}"/data/*.json
rm -rf "${PROJECT_FOLDER}"/pdfs/*.pdf
rm -rf "${PROJECT_FOLDER}"/pngs/*.png
rm -rf "${PROJECT_FOLDER}"/pngs_cropped/*.png
