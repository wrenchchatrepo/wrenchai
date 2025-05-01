#!/bin/bash

# repo_inventory.sh - Create a detailed inventory of repository files
# chmod +x repo_inventory.sh
# Set the maximum depth to explore
MAX_DEPTH=5

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

# Create temporary files for directory statistics
TEMP_DIR_STATS=$(mktemp)
TEMP_FILE_LIST=$(mktemp)

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

# First, collect all files and their info
find "$REPO_DIR" -mindepth 1 -maxdepth "$MAX_DEPTH" | sort | while read -r item; do
    # Skip sensitive files like .env
    if [[ "$item" == *".env"* ]] || [[ "$item" == *"id_rsa"* ]] || [[ "$item" == *".pem"* ]] || [[ "$item" == *"secrets"* ]] || [[ "$item" == *"credential"* ]]; then
        echo "[SENSITIVE FILE SKIPPED] $item" >> "$OUTPUT_FILE"
        continue
    fi
    
    # Calculate the depth relative to REPO_DIR
    rel_path=${item#$REPO_DIR}
    rel_path=${rel_path#/}  # Remove leading slash if present
    depth=$(echo "$rel_path" | tr -cd '/' | wc -c)
    depth=$((depth + 1))
    
    # Skip if depth is greater than MAX_DEPTH
    if [ "$depth" -gt "$MAX_DEPTH" ]; then
        continue
    fi
    
    # Get file type
    ftype=$(get_file_type "$item")
    
    # Get file size (0 for directories)
    if [ -d "$item" ]; then
        size=0
    else
        size=$(stat -f "%z" "$item" 2>/dev/null || stat -c "%s" "$item" 2>/dev/null)
    fi
    
    # Store the file info for processing directory stats
    echo "$item|$rel_path|$depth|$ftype|$size" >> "$TEMP_FILE_LIST"
done

# Calculate stats for each directory
GRAND_TOTAL_SIZE=0
GRAND_TOTAL_FILES=0

# Process all directories first
grep "|dir|" "$TEMP_FILE_LIST" | while read -r line; do
    dir=$(echo "$line" | cut -d'|' -f1)
    rel_dir=$(echo "$line" | cut -d'|' -f2)
    depth=$(echo "$line" | cut -d'|' -f3)
    
    # Initialize directory stats
    echo "$dir|$rel_dir|$depth|0|0" >> "$TEMP_DIR_STATS"
done

# Process all files and update directory stats
grep -v "|dir|" "$TEMP_FILE_LIST" | while read -r line; do
    file=$(echo "$line" | cut -d'|' -f1)
    size=$(echo "$line" | cut -d'|' -f5)
    
    # Increment grand total
    GRAND_TOTAL_SIZE=$((GRAND_TOTAL_SIZE + size))
    GRAND_TOTAL_FILES=$((GRAND_TOTAL_FILES + 1))
    
    # Update stats for all parent directories
    dir=$(dirname "$file")
    while [[ "$dir" != "." && "$dir" != "/" && "$dir" == *"$REPO_DIR"* ]]; do
        # Find the directory in the stats file
        if grep -q "^$dir|" "$TEMP_DIR_STATS"; then
            # Get current stats
            current_line=$(grep "^$dir|" "$TEMP_DIR_STATS")
            current_size=$(echo "$current_line" | cut -d'|' -f4)
            current_files=$(echo "$current_line" | cut -d'|' -f5)
            
            # Update stats
            new_size=$((current_size + size))
            new_files=$((current_files + 1))
            
            # Replace the line - using perl instead of sed for better compatibility
            perl -i -pe "s|^\Q$dir\E\|.*|$dir|$(echo "$current_line" | cut -d'|' -f2)|$(echo "$current_line" | cut -d'|' -f3)|$new_size|$new_files|" "$TEMP_DIR_STATS"
        fi
        
        # Move up to parent directory
        dir=$(dirname "$dir")
    done
done

# Now write the output file with detailed inventory
while read -r line; do
    item=$(echo "$line" | cut -d'|' -f1)
    rel_path=$(echo "$line" | cut -d'|' -f2)
    depth=$(echo "$line" | cut -d'|' -f3)
    ftype=$(echo "$line" | cut -d'|' -f4)
    size=$(echo "$line" | cut -d'|' -f5)
    
    # Get indentation based on depth
    indent=$(printf "%${depth}s" "")
    
    # Format size
    if [ "$ftype" = "dir" ]; then
        # For directories, get cumulative size and file count from stats
        if grep -q "^$item|" "$TEMP_DIR_STATS"; then
            dir_stats=$(grep "^$item|" "$TEMP_DIR_STATS")
            cum_size=$(echo "$dir_stats" | cut -d'|' -f4)
            file_count=$(echo "$dir_stats" | cut -d'|' -f5)
            formatted_size=$(format_size "$cum_size")
        else
            formatted_size="-"
            file_count=0
        fi
    else
        formatted_size=$(format_size "$size")
        file_count="-"
    fi
    
    # Write to output file
    echo "[$depth] [$ftype] [$formatted_size] [$file_count] $rel_path" >> "$OUTPUT_FILE"
done < "$TEMP_FILE_LIST"

echo "" >> "$OUTPUT_FILE"
echo "SUMMARY STATISTICS" >> "$OUTPUT_FILE"
echo "==================" >> "$OUTPUT_FILE"
echo "Total Files: $GRAND_TOTAL_FILES" >> "$OUTPUT_FILE"
echo "Total Size: $(format_size $GRAND_TOTAL_SIZE)" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Directory summary
echo "DIRECTORY SUMMARY (sorted by size)" >> "$OUTPUT_FILE"
echo "==================" >> "$OUTPUT_FILE"
echo "[SIZE] [FILES] [DIRECTORY]" >> "$OUTPUT_FILE"

# Sort directories by size and output
while read -r line; do
    dir=$(echo "$line" | cut -d'|' -f1)
    rel_dir=$(echo "$line" | cut -d'|' -f2)
    if [ -z "$rel_dir" ]; then
        rel_dir="."
    fi
    size=$(echo "$line" | cut -d'|' -f4)
    files=$(echo "$line" | cut -d'|' -f5)
    
    if [ "$size" -gt 0 ]; then
        echo "$size|$files|$rel_dir"
    fi
done < "$TEMP_DIR_STATS" | sort -nr | while read -r line; do
    size=$(echo "$line" | cut -d'|' -f1)
    files=$(echo "$line" | cut -d'|' -f2)
    rel_dir=$(echo "$line" | cut -d'|' -f3)
    
    echo "[$(format_size $size)] [$files] $rel_dir" >> "$OUTPUT_FILE"
done

echo "" >> "$OUTPUT_FILE"
echo "Inventory complete. Total items: $(grep -c '\[.*\]' "$OUTPUT_FILE")" >> "$OUTPUT_FILE"

# Clean up temp files
rm -f "$TEMP_FILE_LIST" "$TEMP_DIR_STATS"

echo "Repository inventory created at: $OUTPUT_FILE"
echo "SECURITY REMINDER: Please review the inventory file before sharing to ensure no sensitive information is included."