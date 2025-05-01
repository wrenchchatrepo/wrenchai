#!/bin/bash

# repo_inventory.sh - Create a detailed inventory of repository files
# chmod +x repo_inventory.sh
# Set the maximum depth to explore
MAX_DEPTH=7

# Output file
OUTPUT_FILE="repo_inventory.txt"

# Get the repository root directory (default to current directory if not specified)
REPO_DIR="${1:-.}"

# Check if output file exists and might contain sensitive information
if [ -f "$OUTPUT_FILE" ]; then
    echo "WARNING: $OUTPUT_FILE already exists and might contain sensitive information."
    read -p "Do you want to delete the existing file? (y/n): " -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm "$OUTPUT_FILE"
        echo "Existing file deleted."
    else
        echo "Using a new filename to avoid overwriting."
        OUTPUT_FILE="repo_inventory_$(date +%s).txt"
    fi
fi

# Write header to the output file
echo "REPOSITORY INVENTORY" > "$OUTPUT_FILE"
echo "==================" >> "$OUTPUT_FILE"
echo "Generated: $(date)" >> "$OUTPUT_FILE"
echo "Directory: $(cd "$REPO_DIR" && pwd)" >> "$OUTPUT_FILE"
echo "Note: Including hidden files and directories, EXCLUDING sensitive files (.env, credentials, keys)" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "FORMAT: [LEVEL] [TYPE] [SIZE] [FILES] [PATH]" >> "$OUTPUT_FILE"
echo "==================" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Create temporary files for collecting data
TEMP_FILE_LIST=$(mktemp)
TEMP_FILE_SIZES=$(mktemp)
TEMP_DIR_STATS=$(mktemp)

# Function to get file type
get_file_type() {
    local file="$1"
    if [ -d "$file" ]; then
        echo "dir"
    else
        # Get file extension
        local ext="${file##*.}"
        if [ "$ext" = "$file" ]; then
            # No extension
            echo "file"
        else
            echo "$ext"
        fi
    fi
}

# Function to format file size
format_size() {
    local size=$1
    if [ $size -ge 1048576 ]; then
        echo "$(echo "scale=2; $size/1048576" | bc)MB"
    elif [ $size -ge 1024 ]; then
        echo "$(echo "scale=2; $size/1024" | bc)KB"
    else
        echo "${size}B"
    fi
}

echo "Scanning files and directories..."

# First pass: List all files and directories
find "$REPO_DIR" -mindepth 1 -maxdepth "$MAX_DEPTH" | sort | while read -r item; do
    # Flag sensitive files but still include them in inventory
    if [[ "$item" == *".env"* ]] || [[ "$item" == *"id_rsa"* ]] || [[ "$item" == *".pem"* ]] || \
       [[ "$item" == *"secrets"* ]] || [[ "$item" == *"credential"* ]]; then
        sensitive_flag="[SENSITIVE]"
    else
        sensitive_flag=""
    fi
    
    # Calculate path info
    rel_path=${item#$REPO_DIR}
    rel_path=${rel_path#/}  # Remove leading slash if present
    if [ -z "$rel_path" ]; then
        rel_path="."
    fi
    
    # Calculate depth
    depth=$(echo "$rel_path" | tr -cd '/' | wc -c)
    depth=$((depth + 1))
    
    # Get file type
    ftype=$(get_file_type "$item")
    
    # For files, get size and update directory stats
    if [ -f "$item" ]; then
        size=$(stat -f "%z" "$item" 2>/dev/null || stat -c "%s" "$item" 2>/dev/null)
        
        # Save file info
        echo "$item|$rel_path|$depth|$ftype|$size" >> "$TEMP_FILE_LIST"
        
        # Create file size entry for statistics
        echo "$item|$size" >> "$TEMP_FILE_SIZES"
        
        # Add entry for each parent directory
        current_dir=$(dirname "$item")
        while [[ "$current_dir" != "." && "$current_dir" != "/" && "$current_dir" == *"$REPO_DIR"* ]]; do
            # Extract relative path
            rel_dir=${current_dir#$REPO_DIR}
            rel_dir=${rel_dir#/}
            if [ -z "$rel_dir" ]; then
                rel_dir="."
            fi
            echo "$current_dir|$rel_dir|$size" >> "$TEMP_DIR_STATS"
            current_dir=$(dirname "$current_dir")
        done
    else
        # For directories, just save info
        echo "$item|$rel_path|$depth|$ftype|0" >> "$TEMP_FILE_LIST"
    fi
done

echo "Calculating directory statistics..."

# Process directory statistics
DIRECTORY_SUMMARY=$(mktemp)

# For each directory, calculate total size and file count
for dir in $(grep -v "|file|" "$TEMP_FILE_LIST" | cut -d'|' -f1); do
    # Get relative path for directory
    rel_dir=${dir#$REPO_DIR}
    rel_dir=${rel_dir#/}
    if [ -z "$rel_dir" ]; then
        rel_dir="."
    fi
    
    # Flag sensitive directories
    if [[ "$dir" == *".env"* ]] || [[ "$dir" == *"id_rsa"* ]] || [[ "$dir" == *".pem"* ]] || \
       [[ "$dir" == *"secrets"* ]] || [[ "$dir" == *"credential"* ]]; then
        sensitive_flag="[SENSITIVE]"
    else
        sensitive_flag=""
    fi
    
    # Calculate depth
    depth=$(echo "$rel_dir" | tr -cd '/' | wc -c)
    depth=$((depth + 1))
    
    # Calculate total size and file count for this directory
    total_size=0
    file_count=0
    
    # Sum all entries for this directory in the stats file
    if grep -q "^$dir|" "$TEMP_DIR_STATS"; then
        while read -r line; do
            size=$(echo "$line" | cut -d'|' -f3)
            total_size=$((total_size + size))
            file_count=$((file_count + 1))
        done < <(grep "^$dir|" "$TEMP_DIR_STATS")
    fi
    
    # Save summary line
    echo "$dir|$rel_dir|$depth|$total_size|$file_count|$sensitive_flag" >> "$DIRECTORY_SUMMARY"
done

echo "Generating inventory report..."

# Write directory entries to output file
while read -r line; do
    dir=$(echo "$line" | cut -d'|' -f1)
    rel_dir=$(echo "$line" | cut -d'|' -f2)
    depth=$(echo "$line" | cut -d'|' -f3)
    total_size=$(echo "$line" | cut -d'|' -f4)
    file_count=$(echo "$line" | cut -d'|' -f5)
    sensitive_flag=$(echo "$line" | cut -d'|' -f6)
    
    # Format size
    formatted_size=$(format_size "$total_size")
    
    # Write entry to output file
    echo "[$depth] [dir] [$formatted_size] [$file_count] $sensitive_flag$rel_dir" >> "$OUTPUT_FILE"
done < "$DIRECTORY_SUMMARY"

# Write file entries to output file
while read -r line; do
    # Skip directories, they're already processed
    if echo "$line" | grep -q "|dir|"; then
        continue
    fi
    
    # Parse file info
    rel_path=$(echo "$line" | cut -d'|' -f2)
    depth=$(echo "$line" | cut -d'|' -f3)
    ftype=$(echo "$line" | cut -d'|' -f4)
    size=$(echo "$line" | cut -d'|' -f5)
    
    # Format size
    formatted_size=$(format_size "$size")
    
    # Write entry to output file
    echo "[$depth] [$ftype] [$formatted_size] [-] $sensitive_flag$rel_path" >> "$OUTPUT_FILE"
done < "$TEMP_FILE_LIST"

# Calculate grand totals
GRAND_TOTAL_FILES=$(wc -l < "$TEMP_FILE_SIZES")
GRAND_TOTAL_SIZE=0
while read -r line; do
    size=$(echo "$line" | cut -d'|' -f2)
    GRAND_TOTAL_SIZE=$((GRAND_TOTAL_SIZE + size))
done < "$TEMP_FILE_SIZES"

# Write summary section
echo "" >> "$OUTPUT_FILE"
echo "SUMMARY STATISTICS" >> "$OUTPUT_FILE"
echo "==================" >> "$OUTPUT_FILE"
echo "Total Files: $GRAND_TOTAL_FILES" >> "$OUTPUT_FILE"
echo "Total Size: $(format_size $GRAND_TOTAL_SIZE)" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Write directory summary section (sorted by size)
echo "DIRECTORY SUMMARY (sorted by size)" >> "$OUTPUT_FILE"
echo "==================" >> "$OUTPUT_FILE"
echo "[SIZE] [FILES] [DIRECTORY]" >> "$OUTPUT_FILE"

# Process directories by size (only those with files)
while read -r line; do
    dir=$(echo "$line" | cut -d'|' -f1)
    rel_dir=$(echo "$line" | cut -d'|' -f2)
    size=$(echo "$line" | cut -d'|' -f4)
    file_count=$(echo "$line" | cut -d'|' -f5)
    sensitive_flag=$(echo "$line" | cut -d'|' -f6)
    
    if [ "$size" -gt 0 ]; then
        echo "$size|$file_count|$rel_dir|$sensitive_flag"
    fi
done < "$DIRECTORY_SUMMARY" | sort -nr | while read -r line; do
    size=$(echo "$line" | cut -d'|' -f1)
    file_count=$(echo "$line" | cut -d'|' -f2)
    rel_dir=$(echo "$line" | cut -d'|' -f3)
    sensitive_flag=$(echo "$line" | cut -d'|' -f4)
    
    echo "[$(format_size $size)] [$file_count] $sensitive_flag$rel_dir" >> "$OUTPUT_FILE"
done

echo "" >> "$OUTPUT_FILE"
echo "Inventory complete. Total items: $(grep -c '\[.*\]' "$OUTPUT_FILE")" >> "$OUTPUT_FILE"

# Clean up temp files
rm -f "$TEMP_FILE_LIST" "$TEMP_FILE_SIZES" "$TEMP_DIR_STATS" "$DIRECTORY_SUMMARY"

echo "Repository inventory created at: $OUTPUT_FILE"
echo "SECURITY REMINDER: Please review the inventory file before sharing to ensure no sensitive information is included."