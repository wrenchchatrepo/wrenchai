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
echo "Note: Shows all files including hidden ones, with sensitive files flagged" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "FORMAT: [LEVEL] [TYPE] [SIZE] [FILES] [PATH]" >> "$OUTPUT_FILE"
echo "==================" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Create temporary files for collecting data
TEMP_FILES=$(mktemp)
TEMP_DIRS=$(mktemp)
DIR_SIZES=$(mktemp)

# Function to get file type based on extension
get_file_type() {
    # Get file extension
    local filename=$(basename "$1")
    local ext="${filename##*.}"
    
    # Check if there's an extension
    if [ "$ext" = "$filename" ]; then
        echo "file"
    else
        echo "$ext"
    fi
}

# Function to format file size
format_size() {
    local size=$1
    if [ "$size" -eq 0 ]; then
        echo "0B"
    elif [ "$size" -ge 1048576 ]; then
        echo "$(echo "scale=2; $size/1048576" | bc)MB"
    elif [ "$size" -ge 1024 ]; then
        echo "$(echo "scale=2; $size/1024" | bc)KB"
    else
        echo "${size}B"
    fi
}

# Function to check if path is sensitive
is_sensitive() {
    local path="$1"
    if [[ "$path" == *".env"* ]] || \
       [[ "$path" == *"id_rsa"* ]] || \
       [[ "$path" == *".pem"* ]] || \
       [[ "$path" == *"secrets"* ]] || \
       [[ "$path" == *"credential"* ]]; then
        echo "[SENSITIVE]"
    else
        echo ""
    fi
}

echo "Phase 1: Collecting file and directory information..."

# Collect file information first
find "$REPO_DIR" -type f -mindepth 1 -maxdepth "$MAX_DEPTH" -print0 | while IFS= read -r -d '' file; do
    # Get file size
    size=$(stat -f "%z" "$file" 2>/dev/null || stat -c "%s" "$file" 2>/dev/null)
    
    # Calculate path info
    rel_path=${file#$REPO_DIR}
    rel_path=${rel_path#/}  # Remove leading slash if present
    if [ -z "$rel_path" ]; then
        rel_path="."
    fi
    
    # Calculate depth
    depth=$(echo "$rel_path" | tr -cd '/' | wc -c)
    depth=$((depth + 1))
    
    # Get sensitive flag
    sensitive_flag=$(is_sensitive "$file")
    
    # Get file type
    ftype=$(get_file_type "$file")
    
    # Store file info for later processing
    echo "$file|$rel_path|$depth|$ftype|$size|$sensitive_flag" >> "$TEMP_FILES"
    
    # Store size for parent directory calculations
    dir=$(dirname "$file")
    echo "$dir|$size" >> "$DIR_SIZES"
done

# Collect directory information
find "$REPO_DIR" -type d -mindepth 1 -maxdepth "$MAX_DEPTH" -print0 | while IFS= read -r -d '' dir; do
    # Calculate path info
    rel_dir=${dir#$REPO_DIR}
    rel_dir=${rel_dir#/}
    if [ -z "$rel_dir" ]; then
        rel_dir="."
    fi
    
    # Calculate depth
    depth=$(echo "$rel_dir" | tr -cd '/' | wc -c)
    depth=$((depth + 1))
    
    # Get sensitive flag
    sensitive_flag=$(is_sensitive "$dir")
    
    # Store directory info
    echo "$dir|$rel_dir|$depth|$sensitive_flag" >> "$TEMP_DIRS"
done

echo "Phase 2: Calculating directory sizes and file counts..."

# Calculate directory sizes and file counts (recursive)
cat "$DIR_SIZES" | awk -F'|' '{
    dir[$1] += $2          # Sum sizes for each directory
    count[$1]++           # Count files in each directory
}

END {
    # Output directory sizes and file counts
    for (d in dir) {
        print d "|" dir[d] "|" count[d]
    }
}' > "$DIR_SIZES.tmp"

# Create a comprehensive directory list with path segments
echo "Phase 3: Computing cumulative directory statistics..."

# Process each directory to ensure parent directories are counted
DIR_FULL_STATS=$(mktemp)
while read -r line; do
    dir=$(echo "$line" | cut -d'|' -f1)
    size=$(echo "$line" | cut -d'|' -f2)
    count=$(echo "$line" | cut -d'|' -f3)
    
    # Record this directory's stats
    echo "$dir|$size|$count" >> "$DIR_FULL_STATS"
    
    # Also propagate stats to all parent directories (including repo root)
    current="$dir"
    while [[ "$current" != "/" && "$current" != "." ]]; do
        parent=$(dirname "$current")
        if [[ "$parent" == "." ]]; then
            # We're at repo root, include it
            echo "$REPO_DIR|$size|$count" >> "$DIR_FULL_STATS"
            break
        fi
        echo "$parent|$size|$count" >> "$DIR_FULL_STATS"
        current="$parent"
    done
done < "$DIR_SIZES.tmp"

# Calculate cumulative stats for each directory
DIR_SUMMARY=$(mktemp)
cat "$DIR_FULL_STATS" | awk -F'|' '{
    dir[$1] += $2          # Sum sizes for each directory
    count[$1] += $3        # Sum file counts for each directory
}

END {
    # Output directory sizes and file counts
    for (d in dir) {
        print d "|" dir[d] "|" count[d]
    }
}' > "$DIR_SUMMARY"

echo "Phase 4: Generating inventory report..."

# Process directories and write to output
while read -r line; do
    dir=$(echo "$line" | cut -d'|' -f1)
    rel_dir=${dir#$REPO_DIR}
    rel_dir=${rel_dir#/}
    if [ -z "$rel_dir" ]; then
        rel_dir="."
    fi
    size=$(echo "$line" | cut -d'|' -f2)
    file_count=$(echo "$line" | cut -d'|' -f3)
    
    # Find matching entry in TEMP_DIRS for depth and sensitive flag
    dir_info=$(grep "^$dir|" "$TEMP_DIRS" 2>/dev/null)
    if [ -n "$dir_info" ]; then
        depth=$(echo "$dir_info" | cut -d'|' -f3)
        sensitive_flag=$(echo "$dir_info" | cut -d'|' -f4)
        
        # Format size
        formatted_size=$(format_size "$size")
        
        # Write to output file
        echo "[$depth] [dir] [$formatted_size] [$file_count] ${sensitive_flag}${rel_dir}" >> "$OUTPUT_FILE"
    fi
done < "$DIR_SUMMARY"

# Process files and write to output
while read -r line; do
    file=$(echo "$line" | cut -d'|' -f1)
    rel_path=$(echo "$line" | cut -d'|' -f2)
    depth=$(echo "$line" | cut -d'|' -f3)
    ftype=$(echo "$line" | cut -d'|' -f4)
    size=$(echo "$line" | cut -d'|' -f5)
    sensitive_flag=$(echo "$line" | cut -d'|' -f6)
    
    # Format size
    formatted_size=$(format_size "$size")
    
    # Write to output file
    echo "[$depth] [$ftype] [$formatted_size] [-] ${sensitive_flag}${rel_path}" >> "$OUTPUT_FILE"
done < "$TEMP_FILES"

# Calculate grand totals for summary
TOTAL_FILES=$(wc -l < "$TEMP_FILES")
TOTAL_SIZE=0
while read -r line; do
    size=$(echo "$line" | cut -d'|' -f5)
    TOTAL_SIZE=$((TOTAL_SIZE + size))
done < "$TEMP_FILES"

# Write summary information
echo "" >> "$OUTPUT_FILE"
echo "SUMMARY STATISTICS" >> "$OUTPUT_FILE"
echo "==================" >> "$OUTPUT_FILE"
echo "Total Files: $TOTAL_FILES" >> "$OUTPUT_FILE"
echo "Total Size: $(format_size $TOTAL_SIZE)" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Generate directory summary sorted by size
echo "DIRECTORY SUMMARY (sorted by size)" >> "$OUTPUT_FILE"
echo "==================" >> "$OUTPUT_FILE"
echo "[SIZE] [FILES] [DIRECTORY]" >> "$OUTPUT_FILE"

# First include the root directory summary (total repo stats)
root_stats=$(grep "^$REPO_DIR|" "$DIR_SUMMARY" 2>/dev/null)
if [ -n "$root_stats" ]; then
    size=$(echo "$root_stats" | cut -d'|' -f2)
    file_count=$(echo "$root_stats" | cut -d'|' -f3)
    if [ "$size" -gt 0 ]; then
        echo "[$(format_size $size)] [$file_count] TOTAL (all directories)" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
    fi
fi

while read -r line; do
    dir=$(echo "$line" | cut -d'|' -f1)
    size=$(echo "$line" | cut -d'|' -f2)
    file_count=$(echo "$line" | cut -d'|' -f3)
    
    if [ "$size" -gt 0 ]; then
        rel_dir=${dir#$REPO_DIR}
        rel_dir=${rel_dir#/}
        if [ -z "$rel_dir" ]; then
            rel_dir="."
        fi
        
        # Find sensitive flag if it exists
        dir_info=$(grep "^$dir|" "$TEMP_DIRS" 2>/dev/null)
        if [ -n "$dir_info" ]; then
            sensitive_flag=$(echo "$dir_info" | cut -d'|' -f4)
        else
            sensitive_flag=""
        fi
        
        echo "$size|$file_count|$rel_dir|$sensitive_flag"
    fi
done < "$DIR_SUMMARY" | sort -nr | while read -r line; do
    size=$(echo "$line" | cut -d'|' -f1)
    file_count=$(echo "$line" | cut -d'|' -f2)
    rel_dir=$(echo "$line" | cut -d'|' -f3)
    sensitive_flag=$(echo "$line" | cut -d'|' -f4)
    
    echo "[$(format_size $size)] [$file_count] ${sensitive_flag}${rel_dir}" >> "$OUTPUT_FILE"
done

echo "" >> "$OUTPUT_FILE"
echo "Inventory complete. Found $TOTAL_FILES files in $(grep -c '\[dir\]' "$OUTPUT_FILE") directories." >> "$OUTPUT_FILE"

# Clean up temp files
rm -f "$TEMP_FILES" "$TEMP_DIRS" "$DIR_SIZES" "$DIR_SIZES.tmp" "$DIR_FULL_STATS" "$DIR_SUMMARY"

echo "Repository inventory created at: $OUTPUT_FILE"
echo "SECURITY REMINDER: Please review the inventory file before sharing to ensure no sensitive information is included."