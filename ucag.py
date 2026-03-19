r"""
Universal CSV to Axiom Python Script Generator

This script automatically generates Axiom-compatible Python artifact scripts
from CSV files. It reads the CSV headers and creates corresponding .py files
following the template pattern.

Usage:
    python csv_to_axiom_generator.py <input_csv_folder> <output_py_folder>
    
Example:
    python csv_to_axiom_generator.py "./csvs" "./artifacts_py"

    This is a universal python script that points to a folder containing CSV files that you want to use to create a Custom Python Artifact, so that you can put the CSV results into Axiom.

It also does a 'best effort' in determine the DataType, so any columns that are Time/Date or GPS, it will try and apply those data types into the script, so that they are properly represented in Axiom.

Once custom artifact python scripts have been created, put these in the 'plugins' folder in following locations:

AXIOM GUI - C:\Program Files\Magnet Forensics\Magnet AXIOM\AXIOM Process\plugins
AUTOMATE Node - C:\Program Files\Magnet Forensics\Magnet AUTOMATE\agent\AXIOM Process\plugins

Typical use case:
- running a 3rd party tool/script over a phone extraction to get CSV outputs, make custom artifacts, then run CSV files (with newly created custom artifacts) in Axiom to get proper results.  Additionally, run the extraction in Axiom 'nomrally' to get other Artifacts, you will have an Axiom case with CSV results + normal results (more result completeness that is all searchable, filterable, etc) - and put all into Portable Case or Review
- obtain CSV results from another source (like drone data), automatically create custom artifacts and run in Axiom

"""

import csv
import os
import sys
from pathlib import Path
import re

# Ensure console output uses UTF-8 encoding.  When the script is
# executed through a PowerShell wrapper the default code page may be
# a legacy ANSI encoding that cannot represent characters like ✓ or ✗.
# Attempt to reconfigure the text streams early so that subsequent
# print() calls never trigger UnicodeEncodeError.
try:
    # Python 3.7+ provides TextIOBase.reconfigure()
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except AttributeError:
    # Fallback for older versions: wrap the buffer manually.
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")



def sanitize_class_name(name):
    """Convert CSV name to valid Python class name"""
    # Replace special characters and spaces with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    # Remove leading underscores and numbers
    sanitized = re.sub(r'^[0-9_]+', '', sanitized)
    # Remove consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Remove trailing underscores
    sanitized = sanitized.rstrip('_')
    return sanitized if sanitized else "CSVArtifact"


def get_fragment_type(column_name):
    """Determine appropriate fragment type based on column name"""
    column_lower = column_name.lower()
    
    if 'time' in column_lower or 'date' in column_lower or 'timestamp' in column_lower:
        return "Category.DateTime", "FragmentType.DateTime"
    elif 'latitude' in column_lower:
        return "Category.Latitude", "FragmentType.Float"
    elif 'longitude' in column_lower:
        return "Category.Longitude", "FragmentType.Float"
    elif 'lat' in column_lower or 'lon' in column_lower:
        # latitude/longitude shorthand - avoid referencing a non-existent
        # Category.Location. Use the SDK's 'None' category at runtime
        # instead (referenced via getattr) and keep the fragment type
        # as float.
        return "getattr(Category, 'None')", "FragmentType.Float"
    else:
        # Default string-type category.  We cannot simply return
        # "Category.None" because "None" is a Python keyword and
        # writing `Category.None` produces a syntax error when the
        # generated artifact script is parsed.  The Axiom SDK does have a
        # Category member named "None", so we reference it indirectly
        # at runtime using getattr().  This expression is still valid
        # Python source and evaluates to the proper value when imported.
        return "getattr(Category, 'None')", "FragmentType.String"


def read_csv_headers(csv_path):
    """Read the first row of CSV to get column headers"""
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            headers = next(reader)
            return headers
    except Exception as e:
        print(f"Error reading {csv_path}: {e}")
        return None


def generate_fragments(headers):
    """Generate CreateFragments method content"""
    fragments = []
    for col in headers:
        category, frag_type = get_fragment_type(col)
        fragments.append(f'        self.AddFragment("{col}", {category}, {frag_type})')
    return '\n'.join(fragments)


def generate_value_assignments(headers):
    """Generate the try/except blocks for each column value"""
    assignments = []
    for i, col in enumerate(headers):
        try_block = f'''                try:
                    foundHit.AddValue("{col}", row[{i}])
                except:
                    foundHit.AddValue("{col}", 'Error: {{}}. {{}}. script line: {{}}'.format(sys.exc_info()[0],sys.exc_info()[1],sys.exc_info()[2].tb_lineno))'''
        assignments.append(try_block)
    return '\n'.join(assignments)


def generate_header_validation(headers):
    """Generate the header validation check.

    IronPython’s compiler has difficulty reducing long ``or`` chains; by
    comparing the entire ``row`` list to a literal list of expected
    headers we avoid constructing any ``OrExpression`` nodes.
    """
    literal = '[' + ', '.join(f'"{col}"' for col in headers) + ']'
    return f'if row != {literal}:'


def generate_py_content(csv_name, headers):
    """Generate complete Python artifact file content using generic class names"""
    # we intentionally avoid embedding the CSV filename in the class names
    fragments = generate_fragments(headers)
    value_assignments = generate_value_assignments(headers)
    header_validation = generate_header_validation(headers)

    content = f'''from axiom import *

import csv
import datetime
import sys
import codecs
import time
import io

class CSVReader(Artifact):
    def __init__(self):
        self.AddHunter(ReadCSV())

    def GetName(self):
        return "{csv_name}"

    def CreateFragments(self):
{fragments}

class ReadCSV(Hunter):
    def Register(self, registrar):
        registrar.RegisterFileName("{csv_name}.csv")

    def Hunt(self, context):
        temp_file_path = context.Searchable.SaveAsTempFile()

        skip_bom = False

        with io.open(temp_file_path, mode="rb") as csv_file:
            bom = csv_file.read(3)

            if bom == codecs.BOM_UTF8:
                skip_bom = True

        with codecs.open(temp_file_path,"rb","utf-8") as csv_file:
            if skip_bom:
                csv_file.seek(len(codecs.BOM_UTF8))

            csv_reader = csv.reader(csv_file, delimiter=",")

            for row in csv_reader:
                if csv_reader.line_num == 1:
                    {header_validation}
                        break
                    else:
                        continue

                foundHit = Hit()
                foundHit.SetLocation("Line Number: " + str(csv_reader.line_num))
{value_assignments}
                self.PublishHit(foundHit)

RegisterArtifact(CSVReader())
'''
    return content


def process_csvs(input_dir, output_dir):
    """Process all CSV files in input directory"""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)

    # remove any existing .py files to avoid stale/legacy artifacts
    for old in output_path.glob('*.py'):
        try:
            old.unlink()
        except Exception:
            pass

    if not input_path.exists():
        print(f"Error: Input directory '{input_dir}' does not exist")
        return False
    
    csv_files = list(input_path.glob('*.csv'))
    
    if not csv_files:
        print(f"No CSV files found in '{input_dir}'")
        return False
    
    print(f"Found {len(csv_files)} CSV file(s)")
    
    success_count = 0
    for csv_file in sorted(csv_files):
        csv_name = csv_file.stem
        print(f"\nProcessing: {csv_file.name}")
        
        headers = read_csv_headers(csv_file)
        if not headers:
            print(f"  ✗ Failed to read headers")
            continue
        
        print(f"  Columns: {len(headers)}")
        
        try:
            py_content = generate_py_content(csv_name, headers)
            
            filename_safe = sanitize_class_name(csv_name)
            output_file = output_path / f"{filename_safe}.py"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(py_content)
            
            print(f"  ✓ Generated: {output_file.name}")
            success_count += 1
            
        except Exception as e:
            print(f"  ✗ Error generating file: {e}")
    
    print(f"\n{'='*60}")
    print(f"Complete: {success_count}/{len(csv_files)} files generated successfully")
    print(f"Output directory: {output_path.absolute()}")
    
    return success_count > 0


def main():
    if len(sys.argv) != 3:
        print("Usage: python csv_to_axiom_generator.py <input_csv_folder> <output_py_folder>")
        print("\nExample:")
        print("  python csv_to_axiom_generator.py './csv_data' './artifacts_py'")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    
    success = process_csvs(input_dir, output_dir)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
