#!/bin/bash

BASE_URL="https://developer.churchsuite.com"
START_PAGE="/home"
OUTPUT_FILE="CHURCHSUITE_API.md"
TMP_DIR=".churchsuite_tmp"

mkdir -p $TMP_DIR
rm -f $OUTPUT_FILE

echo "# ChurchSuite API Documentation" > $OUTPUT_FILE
echo "" >> $OUTPUT_FILE

 # Get all internal links to API doc pages
echo "Fetching all ChurchSuite doc links..."
urls=$(wget -qO- "$BASE_URL$START_PAGE" \
  | grep -oP 'href="\K/[^"]+' \
  | grep -v '^/$' \
  | sed 's|^|'"$BASE_URL"'|' \
  | grep -E '^https://developer.churchsuite.com/(api|integration|webhooks|home)' \
  | sort -u)

if [ -z "$urls" ]; then
  echo "⚠️ No valid documentation URLs found. Exiting."
  exit 1
fi

echo "Found $(echo "$urls" | wc -l) URLs"
echo "$urls" | while read -r full_url; do
  echo "  - Fetching: $full_url"
  slug=$(echo "$full_url" | sed 's|https://||g' | tr '/' '_' | tr '?' '_')
  page_file="$TMP_DIR/$slug.html"
  wget -q -O "$page_file" "$full_url"
  if [[ -s "$page_file" ]]; then
    echo "    ✔ Saved HTML: $page_file ($(wc -c < "$page_file") bytes)"
  else
    echo "    ⚠️ Empty or missing HTML: $page_file"
  fi
  markdown=$(pandoc -f html -t markdown "$page_file")
  echo "    ✔ Markdown length: ${#markdown} characters"
  echo -e "\n## $full_url\n\n$markdown\n" >> "$OUTPUT_FILE"
done

echo "✅ Docs saved to: $OUTPUT_FILE"